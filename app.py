import os
import json
import uuid
import base64
import time
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path

WIB_TZ = timezone(timedelta(hours=7))

def parse_to_wib_date_str(raw_date) -> str:
    if not raw_date or str(raw_date).strip() in ["-", "", "None"]:
        return "-"
    try:
        clean = str(raw_date).strip()
        if "T" in clean or clean.endswith("Z"):
            dt = datetime.fromisoformat(clean.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(WIB_TZ).strftime("%Y-%m-%d")
        elif "/" in clean:
            parts = clean.split(" ")[0].split("/")
            if len(parts) == 3 and len(parts[2]) == 4:
                return f"{parts[2]}-{int(parts[0]):02d}-{int(parts[1]):02d}"
        return clean.split(" ")[0]
    except Exception:
        return str(raw_date).split("T")[0]
from flask import Flask, request, jsonify, send_from_directory, render_template

from config import load_config, save_config
from client_manager import load_clients, save_clients, resolve_client, record_alias_learning
from gemini_service import extract_invoice_data
from sheets_service import send_to_google_sheets, fetch_all_sheet_records, update_google_sheet_record
from notifier_service import (
    send_telegram_notification,
    send_whatsapp_notification,
    format_rupiah
)

import shutil

BASE_DIR = Path(__file__).resolve().parent

if os.environ.get("VERCEL"):
    UPLOAD_DIR = Path("/tmp/uploads")
    DATA_DIR = Path("/tmp/data")
else:
    UPLOAD_DIR = BASE_DIR / "uploads"
    DATA_DIR = BASE_DIR / "data"

try:
    UPLOAD_DIR.mkdir(exist_ok=True, parents=True)
    DATA_DIR.mkdir(exist_ok=True, parents=True)
except Exception:
    pass

STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
HISTORY_FILE = DATA_DIR / "history.json"
ORIGINAL_HISTORY = BASE_DIR / "data" / "history.json"

if os.environ.get("VERCEL") and not HISTORY_FILE.exists() and ORIGINAL_HISTORY.exists():
    try:
        shutil.copy(ORIGINAL_HISTORY, HISTORY_FILE)
    except Exception:
        pass

app = Flask(
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR)
)

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}

def load_local_history() -> list:
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_local_history(records: list):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(records[:500], f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Error saving history] {e}")

def append_local_history(record: dict):
    history = load_local_history()
    # Hindari duplikat jika no_invoice sudah ada
    inv = record.get("invoice_number")
    history = [h for h in history if str(h.get("invoice_number")) != str(inv)]
    history.insert(0, record)
    save_local_history(history)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(str(UPLOAD_DIR), filename)

@app.route("/api/extract", methods=["POST"])
def api_extract():
    if "file" not in request.files:
        return jsonify({"success": False, "message": "Tidak ada file yang diunggah."}), 400
        
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "message": "Nama file kosong."}), 400
        
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({
            "success": False,
            "message": f"Format file '{ext}' tidak didukung. Gunakan PDF, JPG, PNG, atau WEBP."
        }), 400
        
    mime_type = "application/pdf" if ext == ".pdf" else f"image/{ext.replace('.', '')}"
    if ext in [".jpg", ".jpeg"]:
        mime_type = "image/jpeg"
        
    safe_name = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    save_path = UPLOAD_DIR / safe_name
    file_bytes = file.read()
    with open(save_path, "wb") as f:
        f.write(file_bytes)
        
    config = load_config()
    api_key = config.get("gemini_api_key", "").strip()
    if not api_key:
        return jsonify({
            "success": False,
            "message": "Gemini API Key belum diisi! Buka tab 'Pengaturan' dan masukkan API Key Anda.",
            "file_url": f"/uploads/{safe_name}",
            "file_name": file.filename,
            "stored_filename": safe_name,
            "is_pdf": ext == ".pdf"
        }), 400
        
    try:
        model_name = config.get("gemini_model", "gemini-3-flash-preview")
        extracted = extract_invoice_data(file_bytes, mime_type, api_key, model_name)
        
        # Selesaikan masalah Inisial / Nama Klien tidak lengkap (Smart Auto-Enrichment)
        client_res = resolve_client(
            extracted.get("customer_name", ""),
            extracted.get("customer_initials", "")
        )
        
        extracted["customer_name"] = client_res["customer_name"]
        extracted["client_enrichment"] = client_res
        
        extracted["file_url"] = f"/uploads/{safe_name}"
        extracted["file_name"] = file.filename
        extracted["stored_filename"] = safe_name
        extracted["file_mime"] = mime_type
        extracted["is_pdf"] = ext == ".pdf"
        
        return jsonify({
            "success": True,
            "data": extracted
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e),
            "file_url": f"/uploads/{safe_name}",
            "file_name": file.filename,
            "stored_filename": safe_name,
            "is_pdf": ext == ".pdf"
        }), 500

@app.route("/api/save", methods=["POST"])
def api_save():
    data = request.json or {}
    config = load_config()
    
    # Siapkan file_base64 jika ada file yang diunggah
    stored_name = data.get("stored_filename")
    if stored_name:
        file_path = UPLOAD_DIR / stored_name
        if file_path.exists():
            try:
                with open(file_path, "rb") as f:
                    data["file_base64"] = base64.b64encode(f.read()).decode("utf-8")
            except Exception as e:
                print(f"[Save] Error reading file for Drive upload: {e}")
                
    webhook_url = config.get("google_sheets_webhook_url", "").strip()
    if not webhook_url:
        return jsonify({
            "success": False,
            "message": "URL Webhook Google Sheets belum diatur di menu Pengaturan!"
        }), 400
        
    sheet_res = send_to_google_sheets(data, webhook_url)
    if not sheet_res.get("success"):
        return jsonify(sheet_res), 500
        
    drive_url = sheet_res.get("drive_url") or "-"
    data["drive_url"] = drive_url
    
    # Catat ke riwayat lokal
    append_local_history(data)
    
    # Auto-learn inisial klien jika ada koreksi nama baru
    raw_initial = data.get("raw_initial") or data.get("customer_initials")
    full_name = data.get("customer_name")
    if raw_initial and full_name:
        record_alias_learning(raw_initial, full_name)
        
    # Notifikasi
    notif_results = {}
    
    if config.get("telegram_enabled"):
        bot_token = config.get("telegram_bot_token")
        chat_id = config.get("telegram_chat_id")
        tg_res = send_telegram_notification(bot_token, chat_id, data, drive_url=drive_url)
        notif_results["telegram"] = tg_res
        
    if config.get("whatsapp_enabled"):
        wa_res = send_whatsapp_notification(config, data, drive_url=drive_url)
        notif_results["whatsapp"] = wa_res
        
    return jsonify({
        "success": True,
        "message": sheet_res.get("message", "Data pemasukan & file bukti berhasil disimpan!"),
        "drive_url": drive_url,
        "notifications": notif_results
    })

@app.route("/api/update-record", methods=["POST"])
def api_update_record():
    data = request.json or {}
    config = load_config()
    webhook_url = config.get("google_sheets_webhook_url", "").strip()
    
    inv_num = str(data.get("invoice_number") or data.get("no_invoice") or "").strip()
    if not inv_num:
        return jsonify({"success": False, "message": "Nomor invoice tidak boleh kosong"}), 400
        
    # 1. Update data di history lokal
    local_history = load_local_history()
    updated = False
    for i, item in enumerate(local_history):
        if str(item.get("invoice_number", "")).strip() == inv_num:
            local_history[i].update({
                "invoice_date": data.get("invoice_date", item.get("invoice_date", "-")),
                "customer_name": data.get("customer_name", item.get("customer_name", "-")),
                "description": data.get("description", item.get("description", "-")),
                "category": data.get("category", item.get("category", "-")),
                "total_amount": float(data.get("total_amount") or 0),
                "payment_method": data.get("payment_method", item.get("payment_method", "-")),
                "status": data.get("status", item.get("status", "Lunas")),
                "notes": data.get("notes", item.get("notes", "-"))
            })
            updated = True
            break
            
    if not updated:
        local_history.insert(0, {
            "invoice_number": inv_num,
            "invoice_date": data.get("invoice_date", "-"),
            "customer_name": data.get("customer_name", "-"),
            "description": data.get("description", "-"),
            "category": data.get("category", "-"),
            "total_amount": float(data.get("total_amount") or 0),
            "payment_method": data.get("payment_method", "-"),
            "status": data.get("status", "Lunas"),
            "drive_url": data.get("drive_url", "-"),
            "notes": data.get("notes", "-")
        })
        
    save_local_history(local_history)
    
    # Perbarui RECORDS_CACHE di memory
    global RECORDS_CACHE
    if RECORDS_CACHE["data"] and "rows" in RECORDS_CACHE["data"]:
        for row in RECORDS_CACHE["data"]["rows"]:
            if str(row.get("invoice_number", "")).strip() == inv_num:
                row.update({
                    "invoice_date": data.get("invoice_date", row.get("invoice_date", "-")),
                    "customer_name": data.get("customer_name", row.get("customer_name", "-")),
                    "description": data.get("description", row.get("description", "-")),
                    "category": data.get("category", row.get("category", "-")),
                    "total_amount": float(data.get("total_amount") or 0),
                    "payment_method": data.get("payment_method", row.get("payment_method", "-")),
                    "status": data.get("status", row.get("status", "Lunas"))
                })
                break
                
    # 2. Kirim update ke Google Sheets secara asynchronous
    if webhook_url:
        def bg_update():
            update_google_sheet_record(data, webhook_url)
        t = threading.Thread(target=bg_update)
        t.daemon = True
        t.start()
        
    return jsonify({
        "success": True,
        "message": f"Transaksi {inv_num} berhasil diperbarui!"
    })

import threading

RECORDS_CACHE = {
    "timestamp": 0,
    "data": None,
    "is_syncing": False
}

def fetch_and_process_sheets(webhook_url: str):
    """
    Mengambil data langsung dari Google Sheets, memadukan dengan data lokal dan mengurutkannya.
    """
    global RECORDS_CACHE
    if not webhook_url:
        return None
        
    sheet_data = fetch_all_sheet_records(webhook_url)
    sheet_rows = sheet_data.get("rows", [])
    if not sheet_rows:
        return None
        
    local_rows = load_local_history()
    local_map = {str(item.get("invoice_number")): item for item in local_rows if item.get("invoice_number") and str(item.get("invoice_number")) != "-"}
    
    final_rows = []
    for r in sheet_rows:
        if isinstance(r, dict):
            inv_num = str(r.get("no_invoice") or r.get("invoice_number") or "-")
            c_name = str(r.get("nama_klien") or r.get("customer_name") or "-")
            
            raw_date = r.get("tanggal") or r.get("invoice_date") or "-"
            inv_date = parse_to_wib_date_str(raw_date)
                
            desc = str(r.get("deskripsi") or r.get("description") or "-")
            cat = str(r.get("kategori") or r.get("category") or "-")
            
            raw_amt = r.get("nominal")
            if raw_amt is None or raw_amt == "":
                raw_amt = r.get("total_amount")
            if raw_amt is None or raw_amt == "":
                raw_amt = r.get("subtotal", 0)
            try:
                total_amt = float(raw_amt or 0)
            except Exception:
                total_amt = 0.0
                
            bank_val = str(r.get("bank") or r.get("payment_method") or "-")
            status_val = str(r.get("status") or "-")
            drive_val = str(r.get("drive_url") or "-")
            row_id = int(r.get("id") or 0)
            
            if inv_num != "-" and inv_num in local_map:
                loc = local_map[inv_num]
                if total_amt == 0 and loc.get("total_amount"):
                    total_amt = float(loc.get("total_amount", 0))
                if (c_name == "-" or not c_name) and loc.get("customer_name"):
                    c_name = loc.get("customer_name")
                if (inv_date == "-" or not inv_date) and loc.get("invoice_date"):
                    inv_date = loc.get("invoice_date")
                if drive_val == "-" and loc.get("drive_url"):
                    drive_val = loc.get("drive_url")
                    
            final_rows.append({
                "id": row_id,
                "invoice_number": inv_num,
                "customer_name": c_name,
                "invoice_date": inv_date,
                "description": desc,
                "category": cat,
                "total_amount": total_amt,
                "payment_method": bank_val,
                "status": status_val,
                "drive_url": drive_val
            })
            
    if final_rows:
        def get_sort_key(item):
            d = str(item.get("invoice_date") or "1970-01-01")
            i = int(item.get("id") or 0)
            return (d, i)
        final_rows.sort(key=get_sort_key, reverse=True)
        save_local_history(final_rows)
        
        target_sheet_url = sheet_data.get("spreadsheet_url") or "https://docs.google.com/spreadsheets/d/1Nsg5mKsy4OE543P1eVkn2212hVuUL-nVvg31myl-jiw/edit?usp=sharing"
        res = {
            "success": True,
            "source": "google_sheets",
            "spreadsheet_url": target_sheet_url,
            "rows": final_rows
        }
        RECORDS_CACHE["data"] = res
        RECORDS_CACHE["timestamp"] = time.time()
        return res
    return None

def sync_sheets_in_background(webhook_url: str):
    """
    Sinkronisasi Google Sheets di latar belakang tanpa menghalangi user (non-blocking).
    """
    global RECORDS_CACHE
    if RECORDS_CACHE["is_syncing"]:
        return
        
    RECORDS_CACHE["is_syncing"] = True
    try:
        fetch_and_process_sheets(webhook_url)
    except Exception as e:
        print(f"[Sync] Latar belakang sync gagal: {e}")
    finally:
        RECORDS_CACHE["is_syncing"] = False

@app.route("/api/records", methods=["GET"])
def api_records():
    """
    Mengambil data riwayat transaksi real-time.
    - Parameter ?force=1 atau ?force=true: Melakukan sinkronisasi langsung ke Google Sheets.
    - Tanpa parameter: Langsung kirim data cache memori/lokal & trigger sync background jika > 5 detik.
    """
    global RECORDS_CACHE
    force = request.args.get("force", "").lower() in ["1", "true", "yes"]
    now = time.time()
    
    config = load_config()
    webhook_url = config.get("google_sheets_webhook_url", "").strip()
    
    # Jika force=true atau belum ada data sama sekali, lakukan sinkronisasi langsung (blocking & realtime)
    if force or (not RECORDS_CACHE["data"] and not load_local_history()):
        fresh = fetch_and_process_sheets(webhook_url)
        if fresh:
            return jsonify(fresh)
            
    # Trigger background sync jika sudah > 5 detik sejak sync terakhir
    if webhook_url and (now - RECORDS_CACHE["timestamp"] > 5) and not RECORDS_CACHE["is_syncing"]:
        t = threading.Thread(target=sync_sheets_in_background, args=(webhook_url,))
        t.daemon = True
        t.start()
        
    # Jika cache memori ada isinya
    if RECORDS_CACHE["data"] and RECORDS_CACHE["data"].get("rows"):
        return jsonify(RECORDS_CACHE["data"])
        
    # Jika ada data lokal
    local_rows = load_local_history()
    if local_rows:
        res = {
            "success": True,
            "source": "local_history",
            "spreadsheet_url": "https://docs.google.com/spreadsheets/d/1Nsg5mKsy4OE543P1eVkn2212hVuUL-nVvg31myl-jiw/edit?usp=sharing",
            "rows": local_rows
        }
        RECORDS_CACHE["data"] = res
        return jsonify(res)
        
    return jsonify({
        "success": True,
        "source": "loading",
        "spreadsheet_url": "https://docs.google.com/spreadsheets/d/1Nsg5mKsy4OE543P1eVkn2212hVuUL-nVvg31myl-jiw/edit?usp=sharing",
        "rows": []
    })

@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    if request.method == "GET":
        cfg = load_config()
        safe_cfg = cfg.copy()
        if safe_cfg.get("gemini_api_key"):
            key = safe_cfg["gemini_api_key"]
            safe_cfg["gemini_api_key_masked"] = key[:6] + "..." + key[-4:] if len(key) > 10 else "***"
        return jsonify(safe_cfg)
        
    new_data = request.json or {}
    if "gemini_api_key" in new_data and new_data["gemini_api_key"].endswith("..."):
        del new_data["gemini_api_key"]
    updated = save_config(new_data)
    return jsonify({"success": True, "config": updated})

@app.route("/api/clients", methods=["GET", "POST"])
def api_clients():
    if request.method == "GET":
        return jsonify(load_clients())
    new_clients = request.json or {}
    save_clients(new_clients)
    return jsonify({"success": True, "clients": load_clients()})

@app.route("/api/test-telegram", methods=["POST"])
def api_test_telegram():
    req = request.json or {}
    config = load_config()
    token = req.get("telegram_bot_token") or config.get("telegram_bot_token")
    chat_id = req.get("telegram_chat_id") or config.get("telegram_chat_id")
    
    sample_data = {
        "invoice_number": "INV-TEST-001",
        "invoice_date": "2026-11-03",
        "customer_name": "Klien Pengujian (Fariz)",
        "description": "Tes Pengiriman Notifikasi Telegram",
        "category": "Testing Sistem",
        "payment_method": "BCA",
        "total_amount": 1500000,
        "status": "Lunas",
        "notes": "Pesan uji coba integrasi langsung."
    }
    sample_drive = "https://drive.google.com/drive/folders/sample"
    res = send_telegram_notification(token, chat_id, sample_data, drive_url=sample_drive)
    return jsonify(res)

@app.route("/api/test-whatsapp", methods=["POST"])
def api_test_whatsapp():
    req = request.json or {}
    cfg = load_config().copy()
    cfg.update(req)
    cfg["whatsapp_enabled"] = True
    
    sample_data = {
        "invoice_number": "INV-TEST-WA",
        "invoice_date": "2026-11-03",
        "customer_name": "Klien Pengujian WhatsApp",
        "description": "Tes Pengiriman Notifikasi WhatsApp",
        "category": "Testing Sistem",
        "payment_method": "BCA",
        "total_amount": 500000,
        "status": "Lunas"
    }
    sample_drive = "https://drive.google.com/drive/folders/sample"
    res = send_whatsapp_notification(cfg, sample_data, drive_url=sample_drive)
    return jsonify(res)

@app.route("/api/test-sheets", methods=["POST"])
def api_test_sheets():
    req = request.json or {}
    config = load_config()
    webhook_url = req.get("google_sheets_webhook_url") or config.get("google_sheets_webhook_url")
    
    sample_data = {
        "invoice_number": "PING-TEST",
        "invoice_date": "2026-11-03",
        "customer_name": "Tes Sambungan Google Sheets & Drive",
        "description": "Uji coba koneksi webhook berhasil",
        "category": "Sistem",
        "subtotal": 100000,
        "tax": 0,
        "discount": 0,
        "total_amount": 100000,
        "payment_method": "BCA",
        "status": "Lunas",
        "notes": "Baris uji coba dari Invoice Income App"
    }
    res = send_to_google_sheets(sample_data, webhook_url)
    return jsonify(res)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"==================================================")
    print(f"🚀 Invoice Income App berjalan di http://localhost:{port}")
    print(f"==================================================")
    app.run(host="0.0.0.0", port=port, debug=False)
