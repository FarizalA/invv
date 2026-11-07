import requests
import json
import os
import subprocess
import shutil

def send_to_google_sheets(data: dict, webhook_url: str) -> dict:
    """
    Mengirimkan payload data pemasukan + file bukti (base64) ke Google Sheets & Google Drive.
    """
    if not webhook_url:
        raise ValueError("URL Webhook Google Sheets belum diatur di menu Pengaturan!")
        
    url = webhook_url.strip()
    
    payload = {
        "invoice_number": data.get("invoice_number", "-"),
        "invoice_date": data.get("invoice_date", "-"),
        "customer_name": data.get("customer_name", "Pelanggan Umum"),
        "address": data.get("address", "-"),
        "description": data.get("description", "-"),
        "category": data.get("category", "Pemasukan"),
        "subtotal": float(data.get("subtotal") or 0),
        "tax": float(data.get("tax") or 0),
        "discount": float(data.get("discount") or 0),
        "total_amount": float(data.get("total_amount") or 0),
        "payment_method": data.get("payment_method", "-"),
        "status": data.get("status", "Lunas"),
        "notes": data.get("notes", "-"),
        "file_base64": data.get("file_base64", ""),
        "file_name": data.get("file_name", ""),
        "file_mime": data.get("file_mime", "")
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        resp = requests.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            allow_redirects=True,
            timeout=40
        )
        
        if resp.status_code == 200:
            try:
                res_json = resp.json()
                return {
                    "success": True,
                    "message": res_json.get("message", "Berhasil dicatat ke Google Sheets & Drive!"),
                    "row": res_json.get("row"),
                    "drive_url": res_json.get("drive_url")
                }
            except Exception:
                return {
                    "success": True,
                    "message": "Data berhasil dikirim ke Google Sheets.",
                    "drive_url": None
                }
        else:
            return {
                "success": False,
                "message": f"Google Sheets merespon status {resp.status_code}: {resp.text[:200]}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"Gagal menghubungi Google Sheets Webhook: {str(e)}"
        }

def update_google_sheet_record(data: dict, webhook_url: str) -> dict:
    """
    Mengirimkan update/edit transaksi ke Google Sheets.
    """
    if not webhook_url:
        return {"success": False, "message": "Webhook URL belum diatur"}
        
    url = webhook_url.strip()
    payload = {
        "action": "update",
        "row_id": data.get("row_id") or data.get("id"),
        "invoice_number": data.get("invoice_number", "-"),
        "invoice_date": data.get("invoice_date", "-"),
        "customer_name": data.get("customer_name", "-"),
        "address": data.get("address", "-"),
        "description": data.get("description", "-"),
        "category": data.get("category", "-"),
        "total_amount": float(data.get("total_amount") or 0),
        "payment_method": data.get("payment_method", "-"),
        "status": data.get("status", "Lunas"),
        "notes": data.get("notes", "-")
    }
    
    headers = {"Content-Type": "application/json"}
    try:
        resp = requests.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            allow_redirects=True,
            timeout=20
        )
        if resp.status_code == 200:
            try:
                res_json = resp.json()
                return {
                    "success": True,
                    "message": res_json.get("message", "Berhasil memperbarui data di Google Sheets!"),
                    "row": res_json.get("row")
                }
            except Exception:
                return {"success": True, "message": "Update berhasil dikirim."}
        else:
            return {"success": False, "message": f"Status {resp.status_code}: {resp.text[:100]}"}
    except Exception as e:
        return {"success": False, "message": f"Gagal update Google Sheets: {str(e)}"}

def delete_google_sheet_record(invoice_number: str, row_id=None, drive_url=None, webhook_url: str = "") -> dict:
    """
    Menghapus baris transaksi di Google Sheets & menghapus file bukti terkait di Google Drive.
    """
    if not webhook_url:
        return {"success": False, "message": "Webhook URL belum diatur"}

    url = webhook_url.strip()
    payload = {
        "action": "delete",
        "invoice_number": invoice_number or "-"
    }
    if row_id is not None:
        try:
            payload["row_id"] = int(row_id)
        except Exception:
            pass
    if drive_url and str(drive_url).strip() not in ["", "-"]:
        payload["drive_url"] = str(drive_url).strip()

    # 1. Coba via curl sistem untuk kecepatan & keandalan eksekusi redirect Google
    curl_bin = shutil.which("curl") or shutil.which("curl.exe") or ("curl.exe" if os.name == "nt" else "curl")
    try:
        json_str = json.dumps(payload)
        res = subprocess.run(
            [curl_bin, "-L", "-s", "-m", "25", "-H", "Content-Type: application/json", "-d", json_str, url],
            capture_output=True,
            text=True,
            timeout=28
        )
        if res.returncode == 0 and res.stdout.strip():
            try:
                data_resp = json.loads(res.stdout)
                return {"success": True, "data": data_resp}
            except Exception:
                return {"success": True, "message": res.stdout[:100]}
    except Exception as e:
        print(f"[SheetsService] Curl delete error: {e}")

    # 2. Fallback via requests
    try:
        resp = requests.post(url, json=payload, timeout=20)
        return {"success": resp.status_code == 200, "message": resp.text[:100]}
    except Exception as e:
        return {"success": False, "message": str(e)}

def fetch_all_sheet_records(webhook_url: str) -> dict:
    """
    Mengambil data riwayat lengkap dari Google Sheets untuk dipantau langsung di Web Dashboard.
    Menggunakan curl cepat untuk menghindari TLS redirect hang pada Windows/Linux.
    """
    if not webhook_url:
        return {"rows": [], "spreadsheet_url": None}
        
    url = webhook_url.strip()
    
    # 1. Coba via curl sistem (sangat cepat & stabil menangani redirect Google Apps Script)
    curl_bin = shutil.which("curl") or shutil.which("curl.exe") or ("curl.exe" if os.name == "nt" else "curl")
    try:
        res = subprocess.run(
            [curl_bin, "-L", "-s", "-m", "25", url],
            capture_output=True,
            text=True,
            timeout=28
        )
        if res.returncode == 0 and res.stdout.strip():
            data = json.loads(res.stdout)
            if isinstance(data, dict) and "rows" in data:
                return data
            elif isinstance(data, list):
                return {"rows": data, "spreadsheet_url": None}
    except Exception as e:
        print(f"[SheetsService] Curl fetch fallback: {e}")

    # 2. Fallback via requests
    try:
        resp = requests.get(url, allow_redirects=True, timeout=10)
        if resp.status_code == 200:
            res_json = resp.json()
            if isinstance(res_json, dict) and "rows" in res_json:
                return res_json
            elif isinstance(res_json, list):
                return {"rows": res_json, "spreadsheet_url": None}
    except Exception as e:
        print(f"[SheetsService] Gagal mengambil data spreadsheet: {e}")
        
    return {"rows": [], "spreadsheet_url": None}
