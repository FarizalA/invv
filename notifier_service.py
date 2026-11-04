import requests
import json

def format_rupiah(nominal) -> str:
    try:
        val = float(nominal or 0)
        return f"Rp {val:,.0f}".replace(",", ".")
    except Exception:
        return f"Rp {nominal}"

def send_telegram_notification(bot_token: str, chat_id: str, data: dict, drive_url: str = "") -> dict:
    if not bot_token or not chat_id:
        return {"success": False, "message": "Bot Token atau Chat ID Telegram belum diisi."}
        
    url = f"https://api.telegram.org/bot{bot_token.strip()}/sendMessage"
    
    total_formatted = format_rupiah(data.get("total_amount", 0))
    
    message = (
        "💰 <b>PEMASUKAN BARU TERCATAT!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📄 <b>No. Invoice / Ref</b>: <code>{data.get('invoice_number', '-')}</code>\n"
        f"📅 <b>Tanggal</b>: {data.get('invoice_date', '-')}\n"
        f"👤 <b>Klien / Pembeli</b>: <b>{data.get('customer_name', '-')}</b>\n"
        f"💼 <b>Deskripsi</b>: {data.get('description', '-')}\n"
        f"🏷️ <b>Kategori</b>: {data.get('category', 'Pemasukan')}\n"
        f"💳 <b>Bank / Rekening</b>: {data.get('payment_method', '-')}\n"
        f"💵 <b>Total Masuk</b>: <b>{total_formatted}</b>\n"
        f"✅ <b>Status</b>: {data.get('status', 'Lunas')}\n"
    )
    if data.get("notes") and data.get("notes") != "-":
        message += f"📝 <b>Catatan</b>: {data.get('notes')}\n"
        
    if drive_url and drive_url.startswith("http"):
        message += f"📁 <b>Bukti di Google Drive</b>: <a href=\"{drive_url}\">Lihat Bukti Dokumen</a>\n"
        
    message += (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📊 <i>Data otomatis tersimpan ke Google Sheets & Google Drive.</i>"
    )
    
    payload = {
        "chat_id": str(chat_id).strip(),
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code == 200:
            return {"success": True, "message": "Notifikasi Telegram berhasil terkirim!"}
        else:
            return {"success": False, "message": f"Telegram Error {resp.status_code}: {resp.text}"}
    except Exception as e:
        return {"success": False, "message": f"Koneksi ke Telegram gagal: {str(e)}"}

def send_whatsapp_notification(config: dict, data: dict, drive_url: str = "") -> dict:
    if not config.get("whatsapp_enabled"):
        return {"success": False, "message": "Notifikasi WhatsApp dinonaktifkan."}
        
    token = config.get("whatsapp_api_token", "").strip()
    target = config.get("whatsapp_target_phone", "").strip()
    provider = config.get("whatsapp_provider", "fonnte").lower()
    
    if not token or not target:
        return {"success": False, "message": "Token WhatsApp atau Nomor Tujuan belum diisi."}
        
    total_formatted = format_rupiah(data.get("total_amount", 0))
    
    message = (
        "*💰 PEMASUKAN BARU TERCATAT!*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"*No. Invoice / Ref*: {data.get('invoice_number', '-')}\n"
        f"*Tanggal*: {data.get('invoice_date', '-')}\n"
        f"*Klien*: {data.get('customer_name', '-')}\n"
        f"*Deskripsi*: {data.get('description', '-')}\n"
        f"*Kategori*: {data.get('category', 'Pemasukan')}\n"
        f"*Bank*: {data.get('payment_method', '-')}\n"
        f"*Total Masuk*: *{total_formatted}*\n"
        f"*Status*: {data.get('status', 'Lunas')}\n"
    )
    if drive_url and drive_url.startswith("http"):
        message += f"*Bukti Drive*: {drive_url}\n"
        
    message += (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "_Data tersimpan otomatis ke Google Sheets & Drive._"
    )
    
    try:
        if provider == "fonnte":
            url = config.get("whatsapp_api_url") or "https://api.fonnte.com/send"
            headers = {"Authorization": token}
            payload = {
                "target": target,
                "message": message,
                "countryCode": "62"
            }
            resp = requests.post(url, data=payload, headers=headers, timeout=15)
        else:
            url = config.get("whatsapp_api_url")
            headers = {"Content-Type": "application/json"}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            payload = {
                "phone": target,
                "message": message,
                "data": data,
                "drive_url": drive_url
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=15)
            
        if resp.status_code in [200, 201]:
            return {"success": True, "message": "Notifikasi WhatsApp berhasil terkirim!"}
        else:
            return {"success": False, "message": f"WhatsApp API Error {resp.status_code}: {resp.text[:200]}"}
            
    except Exception as e:
        return {"success": False, "message": f"Gagal mengirim WhatsApp: {str(e)}"}
