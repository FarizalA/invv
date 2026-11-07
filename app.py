import os
import json
import uuid
import base64
import time
import threading
import requests
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
from sheets_service import send_to_google_sheets, fetch_all_sheet_records, update_google_sheet_record, delete_google_sheet_record
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
app.config["TEMPLATES_AUTO_RELOAD"] = True

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(str(STATIC_DIR), filename)

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

DELETED_FILE = DATA_DIR / "deleted_records.json"

def load_deleted_records() -> dict:
    if DELETED_FILE.exists():
        try:
            with open(DELETED_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {
                    "row_ids": set(int(x) for x in data.get("row_ids", []) if str(x).isdigit()),
                    "invoices": set(str(x).strip() for x in data.get("invoices", []) if x and str(x).strip() != "-")
                }
        except Exception:
            pass
    return {"row_ids": set(), "invoices": set()}

def mark_record_deleted(row_id=None, inv_num=None):
    cur = load_deleted_records()
    if row_id is not None:
        try:
            cur["row_ids"].add(int(row_id))
        except Exception:
            pass
    if inv_num and str(inv_num).strip() not in ["", "-"]:
        cur["invoices"].add(str(inv_num).strip())
    try:
        with open(DELETED_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "row_ids": list(cur["row_ids"]),
                "invoices": list(cur["invoices"])
            }, f, indent=2)
    except Exception as e:
        print(f"[Error saving deleted_records] {e}")

def unmark_record_deleted(row_id=None, inv_num=None):
    cur = load_deleted_records()
    changed = False
    if row_id is not None:
        try:
            rid = int(row_id)
            if rid in cur["row_ids"]:
                cur["row_ids"].discard(rid)
                changed = True
        except Exception:
            pass
    if inv_num and str(inv_num).strip() in cur["invoices"]:
        cur["invoices"].discard(str(inv_num).strip())
        changed = True
    if changed:
        try:
            with open(DELETED_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "row_ids": list(cur["row_ids"]),
                    "invoices": list(cur["invoices"])
                }, f, indent=2)
        except Exception:
            pass

def append_local_history(record: dict):
    history = load_local_history()
    inv = record.get("invoice_number")
    rid = record.get("id")
    unmark_record_deleted(rid, inv)
    # Hindari duplikat jika no_invoice sudah ada
    history = [h for h in history if str(h.get("invoice_number")) != str(inv)]
    history.insert(0, record)
    save_local_history(history)

@app.route("/api/telegram-webhook", methods=["GET", "POST"])
def telegram_webhook():
    if request.method == "GET":
        return jsonify({"ok": True, "message": "Telegram webhook is active"})
        
    update = request.get_json(silent=True, force=True) or {}
    print(f"[Webhook Event] Raw payload received: {update}")
    
    msg = update.get("message", {})
    cb = update.get("callback_query")
    
    chat_id = None
    if msg:
        chat_id = msg.get("chat", {}).get("id")
    elif cb:
        chat_id = cb.get("message", {}).get("chat", {}).get("id")

    if not chat_id:
        return jsonify({"ok": True})

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        try:
            config = load_config()
            token = config.get("telegram_bot_token", "").strip()
        except Exception:
            token = ""

    # 1. Tangani Klik Tombol (Callback Query)
    if cb:
        cb_id = cb.get("id")
        cb_data = cb.get("data", "")
        if cb_id:
            try:
                requests.post(f"https://api.telegram.org/bot{token}/answerCallbackQuery", json={"callback_query_id": cb_id}, timeout=5)
            except Exception:
                pass
                
        if cb_data.startswith("set_prov:"):
            prov = cb_data.split(":", 1)[1]
            try:
                from user_store import set_user_config
                set_user_config(chat_id, {"provider": prov, "state": "awaiting_api_key"})
            except Exception:
                pass
            prompt_key = (
                f"✅ <b>Provider Terpilih: {prov.upper()}</b>\n\n"
                "Silakan <b>paste/tempel API Key</b> kamu langsung ke chat ini.\n\n"
                "<i>Pesan API Key yang kamu kirim akan langsung dihapus otomatis dari chat demi menjaga privasi keamanan.</i>"
            )
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
                "chat_id": chat_id, "text": prompt_key, "parse_mode": "HTML"
            }, timeout=10)
            return jsonify({"ok": True})

    # 2. Tangani Pesan Teks
    if "text" in msg:
        user_text = msg["text"].strip()
        text_cmd = user_text.lower()
        
        # Selalu respon /start dengan tombol provider
        if text_cmd in ["/start", "halo", "hi", "help", "/menu"]:
            welcome_msg = (
                "👋 <b>Halo! Selamat Datang di Bot Keuangan Cerdas.</b>\n\n"
                "📸 <b>Kirim Foto/PDF:</b> Ekstrak nota, simpan ke Drive & Sheets otomatis.\n"
                "💬 <b>Tanya Jawab:</b> Tanya rincian pemasukan & analisis keuangan.\n\n"
                "Silakan pilih AI Provider yang ingin kamu gunakan di bawah ini:"
            )
            kbd = {
                "inline_keyboard": [
                    [{"text": "🔵 Google Gemini", "callback_data": "set_prov:gemini"},
                     {"text": "🟢 OpenAI (ChatGPT)", "callback_data": "set_prov:openai"}],
                    [{"text": "🟣 Anthropic Claude", "callback_data": "set_prov:claude"},
                     {"text": "🟩 NVIDIA NIM", "callback_data": "set_prov:nvidia"}],
                    [{"text": "⚡ Groq Vision", "callback_data": "set_prov:groq"},
                     {"text": "🌐 OpenRouter", "callback_data": "set_prov:openrouter"}]
                ]
            }
            res_send = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
                "chat_id": chat_id, "text": welcome_msg, "parse_mode": "HTML", "reply_markup": kbd
            }, timeout=10)
            print(f"[Webhook /start send] {res_send.status_code} {res_send.text}")
            return jsonify({"ok": True})

        # Cek state apakah user sedang input API Key
        user_state = "idle"
        user_prov = "gemini"
        try:
            from user_store import get_user_config, set_user_config
            u_cfg = get_user_config(chat_id)
            user_state = u_cfg.get("state", "idle")
            user_prov = u_cfg.get("provider", "gemini")
        except Exception:
            pass

        if user_state == "awaiting_api_key":
            try:
                from user_store import set_user_config
                set_user_config(chat_id, {"api_key": user_text, "state": "idle"})
                requests.post(f"https://api.telegram.org/bot{token}/deleteMessage", json={
                    "chat_id": chat_id, "message_id": msg.get("message_id")
                }, timeout=5)
            except Exception:
                pass

            masked = user_text[:6] + "..." + user_text[-4:] if len(user_text) > 10 else "***"
            succ_text = (
                f"🎉 <b>API Key {user_prov.upper()} Berhasil Disimpan!</b>\n\n"
                f"🔑 Kunci aktif: <code>{masked}</code>\n\n"
                "Sekarang kamu bisa langsung:\n"
                "1. 📸 <b>Kirim foto nota / bukti transfer</b> untuk dicatat otomatis.\n"
                "2. 💬 <b>Tanya keuangan</b> langsung di chat ini."
            )
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
                "chat_id": chat_id, "text": succ_text, "parse_mode": "HTML"
            }, timeout=10)
            return jsonify({"ok": True})

        # Tanya Jawab AI
        reply_ai = "Maaf, belum dapat memproses jawaban."
        try:
            from telegram_bot import chat_with_gemini
            config_all = load_config()
            act_key = os.environ.get("GEMINI_API_KEY", "") or config_all.get("gemini_api_key", "")
            act_url = os.environ.get("GOOGLE_SHEETS_WEBHOOK_URL", "") or config_all.get("google_sheets_webhook_url", "")
            reply_ai = chat_with_gemini(user_text, act_key, act_url)
        except Exception as e:
            reply_ai = f"Maaf, terjadi kendala AI: {e}"

        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
            "chat_id": chat_id, "text": reply_ai
        }, timeout=25)
        return jsonify({"ok": True})

    # Kasus 2: Input File Bukti / Foto
    file_id = None
    file_name = "bukti_pemasukan.jpg"
    mime_type = "image/jpeg"
    if "photo" in msg and len(msg["photo"]) > 0:
        file_id = msg["photo"][-1]["file_id"]
        file_name = f"bukti_{int(time.time())}.jpg"
        mime_type = "image/jpeg"
    elif "document" in msg:
        doc = msg["document"]
        file_id = doc.get("file_id")
        file_name = doc.get("file_name", "invoice.pdf")
        mime_type = doc.get("mime_type", "application/pdf")

    if not file_id:
        return jsonify({"ok": True})

    # Kirim status memproses ke chat
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
        "chat_id": chat_id,
        "text": f"⏳ <b>Memproses dokumen ({file_name})...</b>\nMohon tunggu beberapa detik.",
        "parse_mode": "HTML"
    }, timeout=10)

    try:
        # 1. Unduh file dari Telegram
        finfo_res = requests.get(f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}", timeout=15).json()
        fpath = finfo_res.get("result", {}).get("file_path")
        if not fpath:
            raise Exception("Gagal mendapatkan file_path dari Telegram.")
        fbytes = requests.get(f"https://api.telegram.org/file/bot{token}/{fpath}", timeout=30).content

        # 2. Ekstrak data transaksi dengan Multi-AI Provider (BYOK)
        u_cfg = get_user_config(chat_id)
        user_provider = u_cfg.get("provider", "gemini")
        user_api_key = u_cfg.get("api_key") or api_key

        extracted = universal_extract(fbytes, mime_type, provider=user_provider, api_key=user_api_key)

        # 3. Kirim ke Google Sheets & Google Drive
        drive_b64 = base64.b64encode(fbytes).decode("utf-8")
        extracted["drive_file_base64"] = drive_b64
        extracted["drive_file_name"] = file_name
        extracted["drive_file_mime"] = mime_type

        sheet_res = send_to_google_sheets(extracted, webhook_url)
        drive_link = sheet_res.get("drive_file_url", "")

        # 4. Beri notifikasi hasil rapi ke Telegram
        success_msg = (
            "✅ <b>TRANSAKSI BERHASIL DICATAT!</b>\n\n"
            f"📄 <b>No. Ref/Invoice:</b> <code>{extracted.get('invoice_number', '-')}</code>\n"
            f"📅 <b>Tanggal:</b> {extracted.get('date', '-')}\n"
            f"👤 <b>Nama Klien:</b> {extracted.get('customer_name', '-')}\n"
            f"💰 <b>Total Nominal:</b> Rp {int(extracted.get('total_amount', 0)):,}\n"
            f"🏦 <b>Bank/Metode:</b> {extracted.get('bank_name', '-')}\n"
            f"📌 <b>Kategori:</b> {extracted.get('category', '-')}\n\n"
            f"🔗 <a href=\"{drive_link}\">Buka Bukti di Google Drive</a>" if drive_link else ""
        )
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
            "chat_id": chat_id, "text": success_msg, "parse_mode": "HTML", "disable_web_page_preview": False
        }, timeout=10)

    except Exception as e:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
            "chat_id": chat_id, "text": f"❌ <b>Gagal memproses dokumen:</b>\n{e}", "parse_mode": "HTML"
        }, timeout=10)

    return jsonify({"ok": True})

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
        
    is_pdf = ext == ".pdf"
    preview_url = f"/uploads/{safe_name}"
    if not is_pdf and len(file_bytes) < 8 * 1024 * 1024:
        try:
            b64_img = base64.b64encode(file_bytes).decode("utf-8")
            preview_url = f"data:{mime_type};base64,{b64_img}"
        except Exception:
            pass

    config = load_config()
    provider = config.get("ai_provider", "gemini").lower()
    
    # Ambil API key sesuai provider terpilih
    api_key = ""
    if provider == "gemini":
        api_key = config.get("gemini_api_key", "").strip()
    elif provider == "openai":
        api_key = config.get("openai_api_key", "").strip()
    elif provider == "claude":
        api_key = config.get("claude_api_key", "").strip()
    elif provider == "nvidia":
        api_key = config.get("nvidia_api_key", "").strip()
    elif provider == "groq":
        api_key = config.get("groq_api_key", "").strip()
    elif provider == "openrouter":
        api_key = config.get("openrouter_api_key", "").strip()
    elif provider == "agnes":
        api_key = config.get("agnes_api_key", "").strip()
    elif provider == "sumopod":
        api_key = config.get("sumopod_api_key", "").strip()
    else:
        api_key = config.get("gemini_api_key", "").strip()
        provider = "gemini"

    if not api_key:
        return jsonify({
            "success": False,
            "message": f"API Key untuk {provider.upper()} belum diisi! Buka tab 'Pengaturan' dan masukkan API Key Anda.",
            "file_url": preview_url,
            "file_name": file.filename,
            "stored_filename": safe_name,
            "is_pdf": is_pdf
        }), 400
        
    try:
        from multi_ai_service import universal_extract
        extracted = universal_extract(file_bytes, mime_type, provider=provider, api_key=api_key)
        
        # Selesaikan masalah Inisial / Nama Klien tidak lengkap (Smart Auto-Enrichment)
        client_res = resolve_client(
            extracted.get("customer_name", ""),
            extracted.get("customer_initials", "")
        )
        
        extracted["customer_name"] = client_res["customer_name"]
        extracted["client_enrichment"] = client_res
        
        extracted["file_url"] = preview_url
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
            "message": f"Gagal mengekstrak dokumen dengan {provider.upper()} AI: {e}",
            "file_url": preview_url,
            "file_name": file.filename,
            "stored_filename": safe_name,
            "is_pdf": is_pdf
        }), 500

@app.route("/api/save", methods=["POST"])
def api_save():
    data = request.json or {}
    total_val = float(data.get("total_amount") or data.get("nominal") or 0)
    if total_val <= 0:
        return jsonify({
            "success": False,
            "message": "Transaksi ditolak: Nominal transaksi tidak boleh Rp 0!"
        }), 400
    config = load_config()
    
    # Siapkan file_base64 jika ada file yang diunggah (dari disk atau fallback data URL)
    stored_name = data.get("stored_filename")
    if stored_name and not data.get("file_base64"):
        file_path = UPLOAD_DIR / stored_name
        if file_path.exists():
            try:
                with open(file_path, "rb") as f:
                    data["file_base64"] = base64.b64encode(f.read()).decode("utf-8")
            except Exception as e:
                print(f"[Save] Error reading file for Drive upload: {e}")
    if not data.get("file_base64") and data.get("file_data_url"):
        raw_durl = str(data.get("file_data_url"))
        if ";base64," in raw_durl:
            data["file_base64"] = raw_durl.split(";base64,", 1)[1]
                
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
    row_num = sheet_res.get("row")
    data["drive_url"] = drive_url
    if row_num:
        data["id"] = int(row_num)
    
    # Catat ke riwayat lokal & perbarui cache memori secara instan
    append_local_history(data)
    global RECORDS_CACHE
    RECORDS_CACHE["timestamp"] = 0
    if RECORDS_CACHE.get("data") and isinstance(RECORDS_CACHE["data"].get("rows"), list):
        RECORDS_CACHE["data"]["rows"].insert(0, {
            "id": int(row_num) if row_num else 0,
            "invoice_number": data.get("invoice_number", "-"),
            "customer_name": data.get("customer_name", "Pelanggan Umum"),
            "address": data.get("address", "-"),
            "invoice_date": data.get("invoice_date", "-"),
            "description": data.get("description", "-"),
            "category": data.get("category", "Pemasukan"),
            "total_amount": float(data.get("total_amount") or 0),
            "payment_method": data.get("payment_method", "-"),
            "status": data.get("status", "Lunas"),
            "drive_url": drive_url
        })
    
    # Auto-learn inisial klien & kirim notifikasi di background thread agar response instan
    def _post_save_tasks(cfg_copy, data_copy, d_url):
        try:
            raw_init = data_copy.get("raw_initial") or data_copy.get("customer_initials")
            f_name = data_copy.get("customer_name")
            if raw_init and f_name:
                record_alias_learning(raw_init, f_name)
        except Exception:
            pass
        try:
            if cfg_copy.get("telegram_enabled"):
                send_telegram_notification(cfg_copy.get("telegram_bot_token"), cfg_copy.get("telegram_chat_id"), data_copy, drive_url=d_url)
            if cfg_copy.get("whatsapp_enabled"):
                send_whatsapp_notification(cfg_copy, data_copy, drive_url=d_url)
        except Exception as e:
            print(f"[Save Notif Background Error] {e}")

    threading.Thread(target=_post_save_tasks, args=(config, dict(data), drive_url), daemon=True).start()
        
    return jsonify({
        "success": True,
        "message": sheet_res.get("message", "Data pemasukan & file bukti berhasil disimpan!"),
        "drive_url": drive_url,
        "row": row_num
    })

@app.route("/api/delete-record", methods=["POST"])
def api_delete_record():
    data = request.json or {}
    inv_num = str(data.get("invoice_number") or "").strip()
    row_id = data.get("row_id") or data.get("id")
    if not inv_num and not row_id:
        return jsonify({"success": False, "message": "Nomor invoice atau ID baris tidak ditemukan"}), 400

    r_id_int = None
    if row_id:
        try:
            r_id_int = int(row_id)
        except Exception:
            pass

    # Catat ke daftar terhapus permanen agar tidak muncul lagi saat sinkronisasi
    mark_record_deleted(r_id_int, inv_num)

    # 1. Cari drive_url sebelum dihapus & hapus dari history lokal
    local_history = load_local_history()
    drive_url_to_delete = str(data.get("drive_url") or "").strip()
    for item in local_history:
        match_id = (r_id_int is not None and item.get("id") == r_id_int)
        match_inv = (inv_num and inv_num != "-" and str(item.get("invoice_number", "")).strip() == inv_num)
        if match_id or match_inv:
            if not drive_url_to_delete and item.get("drive_url"):
                drive_url_to_delete = str(item.get("drive_url")).strip()
            if not inv_num and item.get("invoice_number"):
                inv_num = str(item.get("invoice_number")).strip()
                mark_record_deleted(r_id_int, inv_num)
            break

    def _should_keep(item):
        if r_id_int is not None and item.get("id") == r_id_int:
            return False
        if inv_num and inv_num != "-" and str(item.get("invoice_number", "")).strip() == inv_num:
            return False
        return True

    new_local = [item for item in local_history if _should_keep(item)]
    save_local_history(new_local)

    # 2. Hapus dari cache memori
    global RECORDS_CACHE
    if RECORDS_CACHE.get("data") and isinstance(RECORDS_CACHE["data"].get("rows"), list):
        if not drive_url_to_delete:
            for item in RECORDS_CACHE["data"]["rows"]:
                if not _should_keep(item):
                    if item.get("drive_url"):
                        drive_url_to_delete = str(item.get("drive_url")).strip()
                    break
        RECORDS_CACHE["data"]["rows"] = [item for item in RECORDS_CACHE["data"]["rows"] if _should_keep(item)]
        RECORDS_CACHE["timestamp"] = time.time()

    # 3. Kirim ke webhook Google Apps Script di background
    # Menggunakan action='update' + sub_action='delete' + status='DIHAPUS' agar:
    # - Jika Apps Script sudah versi terbaru: baris langsung dihapus fisik (sheet.deleteRow) & file Drive dihapus.
    # - Jika Apps Script masih versi lama: baris di-update menjadi status 'DIHAPUS' (nominal 0) dan TIDAK PERNAH menambah baris baru!
    config = load_config()
    webhook_url = config.get("google_sheets_webhook_url", "").strip()
    if webhook_url:
        threading.Thread(
            target=delete_google_sheet_record,
            args=(inv_num, r_id_int, drive_url_to_delete, webhook_url),
            daemon=True
        ).start()

    return jsonify({"success": True, "message": f"Transaksi #{inv_num or row_id} berhasil dihapus!"})


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
                "address": data.get("address", item.get("address", "-")),
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
            "address": data.get("address", "-"),
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
    is_valid_sheet_resp = (sheet_data.get("status") == "success" or bool(sheet_data.get("spreadsheet_url")))
    sheet_rows = sheet_data.get("rows", [])
    if not sheet_rows and not is_valid_sheet_resp:
        return None
        
    local_rows = load_local_history()
    local_map = {str(item.get("invoice_number")): item for item in local_rows if item.get("invoice_number") and str(item.get("invoice_number")) != "-"}
    
    final_rows = []
    for r in sheet_rows:
        if isinstance(r, dict):
            inv_num = str(r.get("no_invoice") or r.get("invoice_number") or "-")
            c_name = str(r.get("nama_klien") or r.get("customer_name") or "-")
            addr = str(r.get("alamat") or r.get("address") or "-")
            
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
            
            # Lewati baris yang sudah dihapus (tombstone lokal atau status DIHAPUS di Sheet) atau baris dummy 0
            deleted_info = load_deleted_records()
            catatan_val = str(r.get("catatan") or r.get("notes") or "-").strip()
            if (
                (inv_num != "-" and inv_num in deleted_info["invoices"])
                or status_val.upper() == "DIHAPUS"
                or c_name.upper() == "DIHAPUS"
                or catatan_val.upper() == "DELETED"
                or (total_amt <= 0 and (desc in ["-", "", "DIHAPUS"] or c_name in ["Pelanggan Umum", "DIHAPUS", "-"]))
            ):
                continue

            if inv_num != "-" and inv_num in local_map:
                loc = local_map[inv_num]
                if (c_name == "-" or not c_name) and loc.get("customer_name"):
                    c_name = loc.get("customer_name")
                if (addr == "-" or not addr) and loc.get("address"):
                    addr = loc.get("address")
                if (inv_date == "-" or not inv_date) and loc.get("invoice_date"):
                    inv_date = loc.get("invoice_date")
                if (desc == "-" or not desc) and loc.get("description"):
                    desc = loc.get("description")
                if (cat == "-" or not cat) and loc.get("category"):
                    cat = loc.get("category")
                if (bank_val == "-" or not bank_val) and loc.get("payment_method"):
                    bank_val = loc.get("payment_method")
                if (status_val == "-" or not status_val) and loc.get("status"):
                    status_val = loc.get("status")
                if (drive_val == "-" or not drive_val or not drive_val.startswith("http")) and loc.get("drive_url") and str(loc.get("drive_url")).startswith("http"):
                    drive_val = loc.get("drive_url")
                    
            row_dict = {
                "id": row_id,
                "invoice_number": inv_num,
                "customer_name": c_name,
                "address": addr,
                "invoice_date": inv_date,
                "description": desc,
                "category": cat,
                "subtotal": float(r.get("subtotal") or 0),
                "tax": float(r.get("pajak") or r.get("tax") or 0),
                "discount": float(r.get("diskon") or r.get("discount") or 0),
                "total_amount": total_amt,
                "payment_method": bank_val,
                "status": status_val,
                "drive_url": drive_val
            }
            if isinstance(r, dict):
                for k, v in r.items():
                    if k not in row_dict and k not in ["no_invoice", "nama_klien", "alamat", "tanggal", "deskripsi", "kategori", "nominal", "bank"]:
                        row_dict[k] = v
            final_rows.append(row_dict)
            
    if final_rows or is_valid_sheet_resp:
        def get_sort_key(item):
            # Prioritaskan ID baris terbesar (paling terakhir di-upload/ditambahkan ke Google Sheets)
            try:
                row_id = int(item.get("id") or 0)
            except Exception:
                row_id = 0
            d = str(item.get("invoice_date") or "1970-01-01")
            return (row_id, d)
        final_rows.sort(key=get_sort_key, reverse=True)
        save_local_history(final_rows)
        
        target_sheet_url = sheet_data.get("spreadsheet_url") or "https://docs.google.com/spreadsheets/d/1Nsg5mKsy4OE543P1eVkn2212hVuUL-nVvg31myl-jiw/edit?usp=sharing"
        drive_folder_url = sheet_data.get("drive_folder_url") or ""
        res = {
            "success": True,
            "source": "google_sheets",
            "spreadsheet_url": target_sheet_url,
            "drive_folder_url": drive_folder_url,
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
        
    # Jika cache memori ada isinya (termasuk jika rows kosong hasil sinkronisasi resmi)
    if RECORDS_CACHE["data"] and "rows" in RECORDS_CACHE["data"]:
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

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.json or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"success": False, "message": "Pesan tidak boleh kosong."}), 400

    config = load_config()
    provider = config.get("ai_provider", "gemini").lower()
    api_key = config.get(f"{provider}_api_key", "").strip()
    
    # Kumpulkan konteks data transaksi untuk AI
    try:
        import app as app_module
        raw_cache = getattr(app_module, "RECORDS_CACHE", None)
        if isinstance(raw_cache, dict) and raw_cache.get("data") and isinstance(raw_cache.get("data"), dict) and "rows" in raw_cache["data"]:
            records = raw_cache["data"]["rows"]
        elif isinstance(raw_cache, list):
            records = raw_cache
        else:
            records = load_local_history() or []
    except Exception:
        records = []

    context_str = f"Data transaksi saat ini ada {len(records)} baris:\n"
    total_rev = 0
    for r in records[:50]:
        total_rev += r.get("total_amount", 0)
        context_str += f"- {r.get('date')}: {r.get('customer_name')} ({r.get('category')}) = Rp {r.get('total_amount', 0):,} [{r.get('status')}]\n"
    context_str += f"\nTotal akumulasi pemasukan: Rp {total_rev:,}"

    system_prompt = (
        "Kamu adalah asisten keuangan pribadi yang profesional, ramah, dan ringkas. "
        "Tugasmu membantu menjawab pertanyaan seputar keuangan, invoice, klien, dan pemasukan pengguna berdasarkan data transaksi berikut:\n\n"
        f"{context_str}\n\n"
        "Jawab dengan singkat, jelas, akurat, dan hindari penggunaan emotikon berlebihan."
    )

    try:
        if not api_key:
            return jsonify({
                "success": True,
                "reply": f"Halo kak! ✨ Total transaksi yang tercatat ada {len(records)} transaksi dengan pemasukan Rp {total_rev:,}. (Catatan: Masukkan API Key di tab Pengaturan agar aku bisa analisa lebih pintar lagi yaa~ 🌸)"
            })

        # Kirim ke AI Provider
        if provider == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": f"{system_prompt}\n\nPertanyaan User: {message}"}]}]
            }
            resp = requests.post(url, json=payload, timeout=20)
            if resp.status_code == 200:
                reply = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                return jsonify({"success": True, "reply": reply})
        else:
            # OpenAI compatible (OpenAI, Claude, NVIDIA, Groq, OpenRouter, Agnes)
            base_urls = {
                "openai": ("https://api.openai.com/v1", "gpt-4o-mini"),
                "agnes": ("https://apihub.agnes-ai.com/v1", "agnes-3.0-flash"),
                "groq": ("https://api.groq.com/openai/v1", "llama-3.1-8b-instant"),
                "openrouter": ("https://openrouter.ai/api/v1", "google/gemini-2.0-flash-exp:free"),
                "nvidia": ("https://integrate.api.nvidia.com/v1", "nvidia/nemotron-3-ultra-550b-a55b"),
                "sumopod": ("https://ai.sumopod.com/v1", "gpt-4o-mini")
            }
            b_url, m_name = base_urls.get(provider, ("https://apihub.agnes-ai.com/v1", "agnes-3.0-flash"))
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": m_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                "temperature": 0.7
            }
            resp = requests.post(f"{b_url}/chat/completions", headers=headers, json=payload, timeout=20)
            if resp.status_code == 200:
                reply = resp.json()["choices"][0]["message"]["content"]
                return jsonify({"success": True, "reply": reply})

        return jsonify({
            "success": True,
            "reply": f"Tercatat {len(records)} transaksi dengan total Rp {total_rev:,}! Ada yang mau ditanyakan lagi kak? ✨"
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/test-ai", methods=["POST"])
def api_test_ai():
    data = request.json or {}
    provider = data.get("provider", "").lower()
    api_key = data.get("api_key", "").strip()

    # Jika dikirim placeholder masked 'nvapi-...' atau 'sk-...', coba ambil dari config tersimpan
    if not api_key or "..." in api_key:
        cfg = load_config()
        api_key = cfg.get(f"{provider}_api_key", "")

    if not api_key:
        return jsonify({"success": False, "message": f"API Key {provider.upper()} belum diisi!"}), 400

    import importlib
    import multi_ai_service
    importlib.reload(multi_ai_service)
    res = multi_ai_service.test_ai_connection(provider, api_key)
    return jsonify(res)


@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    if request.method == "GET":
        cfg = load_config()
        safe_cfg = cfg.copy()
        
        # Masking API Keys demi keamanan tampilan
        for k in ["gemini_api_key", "openai_api_key", "claude_api_key", "nvidia_api_key", "groq_api_key", "openrouter_api_key", "agnes_api_key", "sumopod_api_key"]:
            if safe_cfg.get(k):
                val = safe_cfg[k]
                safe_cfg[f"{k}_masked"] = val[:6] + "..." + val[-4:] if len(val) > 10 else "***"
        return jsonify(safe_cfg)
        
    new_data = request.json or {}
    for k in ["gemini_api_key", "openai_api_key", "claude_api_key", "nvidia_api_key", "groq_api_key", "openrouter_api_key", "agnes_api_key", "sumopod_api_key"]:
        if k in new_data and new_data[k].endswith("..."):
            del new_data[k]
            
    updated = save_config(new_data)
    return jsonify({"success": True, "config": updated})


@app.route("/api/columns", methods=["GET", "POST"])
def api_columns():
    from config import DEFAULT_COLUMNS
    cfg = load_config()
    if request.method == "GET":
        cols = cfg.get("table_columns") or DEFAULT_COLUMNS
        return jsonify({"success": True, "columns": cols})
    
    data = request.json or {}
    new_cols = data.get("columns")
    if isinstance(new_cols, list) and new_cols:
        save_config({"table_columns": new_cols})
        return jsonify({"success": True, "columns": new_cols, "message": "Pengaturan kolom berhasil disimpan!"})
    return jsonify({"success": False, "message": "Format kolom tidak valid."}), 400

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
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=True)
