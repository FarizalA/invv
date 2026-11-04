import time
import base64
import requests
import json
from config import load_config, save_config
from gemini_service import extract_invoice_data
from client_manager import resolve_client, record_alias_learning
from sheets_service import send_to_google_sheets
from notifier_service import format_rupiah

def run_telegram_bot():
    print("=" * 60)
    print("🤖 MEMULAI TELEGRAM BOT INVOICE PEMASUKAN OTOMATIS")
    print("=" * 60)
    
    cfg = load_config()
    token = cfg.get("telegram_bot_token", "").strip()
    
    while not token:
        print("\n⚠️ Telegram Bot Token belum diatur!")
        token = input("Masukkan Bot Token Telegram Anda (dari @BotFather): ").strip()
        if token:
            save_config({"telegram_bot_token": token, "telegram_enabled": True})
            cfg = load_config()
            break
            
    api_key = cfg.get("gemini_api_key", "").strip()
    webhook_url = cfg.get("google_sheets_webhook_url", "").strip()
    
    if not api_key:
        print("❌ Gemini API Key belum diatur!")
        return
    if not webhook_url:
        print("❌ Google Sheets Webhook URL belum diatur!")
        return
        
    print(f"✅ Bot siap mendengarkan pesan foto / PDF...")
    print(f"👉 Silakan kirimkan foto nota atau file PDF ke bot Telegram Anda sekarang!")
    
    offset = None
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{token}/getUpdates?timeout=30"
            if offset:
                url += f"&offset={offset}"
                
            resp = requests.get(url, timeout=35).json()
            
            if not resp.get("ok"):
                time.sleep(3)
                continue
                
            for update in resp.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                
                if not chat_id:
                    continue
                    
                file_id = None
                file_name = "bukti_pemasukan.jpg"
                mime_type = "image/jpeg"
                
                if "photo" in msg and len(msg["photo"]) > 0:
                    # Ambil foto resolusi tertinggi
                    file_id = msg["photo"][-1]["file_id"]
                    file_name = f"bukti_foto_{int(time.time())}.jpg"
                    mime_type = "image/jpeg"
                elif "document" in msg:
                    doc = msg["document"]
                    file_id = doc.get("file_id")
                    file_name = doc.get("file_name", "invoice.pdf")
                    mime_type = doc.get("mime_type", "application/pdf")
                elif "text" in msg:
                    text_cmd = msg["text"].strip().lower()
                    if text_cmd in ["/start", "halo", "hi", "help"]:
                        welcome_msg = (
                            "👋 <b>Halo! Saya Bot Pencatat Pemasukan Otomatis.</b>\n\n"
                            "📸 <b>Cara Pakai:</b>\n"
                            "Kirimkan <b>foto nota, struk kwitansi, bukti transfer, atau file PDF</b> ke chat ini.\n\n"
                            "Saya akan otomatis mengekstrak data transaksi, mengupload bukti ke Google Drive, dan mencatatnya ke Google Sheets!"
                        )
                        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": welcome_msg,
                            "parse_mode": "HTML"
                        })
                    continue
                    
                if file_id:
                    # Beri respon awal bahwa file sedang diproses
                    requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": "⏳ <i>Sedang membaca dokumen & mengekstrak data dengan Gemini AI...</i>",
                        "parse_mode": "HTML"
                    })
                    
                    # 1. Unduh file fisik dari Telegram
                    f_info = requests.get(f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}").json()
                    file_path = f_info.get("result", {}).get("file_path")
                    if not file_path:
                        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": "❌ Gagal mengunduh file dari Telegram."
                        })
                        continue
                        
                    file_bytes = requests.get(f"https://api.telegram.org/file/bot{token}/{file_path}").content
                    
                    # 2. Ekstrak data via Gemini AI
                    try:
                        extracted = extract_invoice_data(file_bytes, mime_type, api_key, "gemini-3-flash-preview")
                    except Exception as e:
                        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": f"❌ Gagal memproses gambar: {str(e)}"
                        })
                        continue
                        
                    # 3. Selesaikan Inisial Klien
                    client_res = resolve_client(extracted.get("customer_name", ""), extracted.get("customer_initials", ""))
                    extracted["customer_name"] = client_res["customer_name"]
                    
                    # 4. Siapkan payload dan kirim ke Google Sheets & Drive
                    extracted["file_base64"] = base64.b64encode(file_bytes).decode("utf-8")
                    extracted["file_name"] = file_name
                    extracted["file_mime"] = mime_type
                    
                    sheet_res = send_to_google_sheets(extracted, webhook_url)
                    
                    if sheet_res.get("success"):
                        drive_url = sheet_res.get("drive_url", "-")
                        total_fmt = format_rupiah(extracted.get("total_amount", 0))
                        
                        reply_text = (
                            "✅ <b>PEMASUKAN BERHASIL DICATAT!</b>\n"
                            "━━━━━━━━━━━━━━━━━━━━\n"
                            f"📄 <b>No. Invoice / Ref</b>: <code>{extracted.get('invoice_number', '-')}</code>\n"
                            f"📅 <b>Tanggal</b>: {extracted.get('invoice_date', '-')}\n"
                            f"👤 <b>Klien / Pembeli</b>: <b>{extracted.get('customer_name', '-')}</b>\n"
                            f"💼 <b>Deskripsi</b>: {extracted.get('description', '-')}\n"
                            f"🏷️ <b>Kategori</b>: {extracted.get('category', 'Pemasukan')}\n"
                            f"💳 <b>Bank Tujuan</b>: {extracted.get('payment_method', '-')}\n"
                            f"💵 <b>Total Masuk</b>: <b>{total_fmt}</b>\n"
                            f"📊 <b>Status</b>: {extracted.get('status', 'Lunas')}\n"
                        )
                        if drive_url and drive_url.startswith("http"):
                            reply_text += f"📁 <a href=\"{drive_url}\">Lihat Bukti di Google Drive</a>\n"
                        reply_text += (
                            "━━━━━━━━━━━━━━━━━━━━\n"
                            "📈 <i>Data otomatis tersimpan ke Google Sheets & Drive.</i>"
                        )
                        
                        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": reply_text,
                            "parse_mode": "HTML"
                        })
                    else:
                        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": f"❌ Gagal menyimpan ke Google Sheets: {sheet_res.get('message')}"
                        })
                        
        except Exception as err:
            print(f"[Bot Error] {err}")
            time.sleep(3)

if __name__ == "__main__":
    run_telegram_bot()
