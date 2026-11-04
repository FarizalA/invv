import time
import base64
import requests
import json
from config import load_config, save_config
from gemini_service import extract_invoice_data
from client_manager import resolve_client, record_alias_learning
from sheets_service import send_to_google_sheets, fetch_all_sheet_records
from notifier_service import format_rupiah

def chat_with_gemini(user_text: str, api_key: str, webhook_url: str, chat_history: list = None) -> str:
    """
    Menjawab pertanyaan pengguna di Telegram layaknya AI Agent Keuangan:
    Membaca data transaksi dari Google Sheets dan menganalisisnya secara kontekstual.
    """
    # 1. Ambil konteks data transaksi terkini dari Google Sheets
    context_rows_str = "Belum ada data transaksi."
    try:
        sheet_data = fetch_all_sheet_records(webhook_url)
        rows = sheet_data.get("rows", [])
        if rows:
            # Ambil hingga 30 baris terbaru untuk konteks prompt AI
            sample_rows = rows[:30]
            context_rows_str = json.dumps(sample_rows, ensure_ascii=False)
    except Exception as e:
        context_rows_str = f"Error membaca sheet: {e}"

    system_instruction = (
        "Kamu adalah Asisten Finansial AI Cerdas untuk Invoice & Pemasukan Usaha. "
        "Tugasmu adalah menjawab pertanyaan pengguna di Telegram dengan ramah, informatif, dan akurat.\n"
        "Berikut adalah data riwayat transaksi pemasukan terbaru dari Google Sheets:\n"
        f"DATA_TRANSAKSI:\n{context_rows_str}\n\n"
        "Panduan:\n"
        "1. Jawab pertanyaan seputar total pemasukan, rincian transaksi klien, tanggal, status lunas, dsb dengan menghitung dari data di atas.\n"
        "2. Format nominal uang selalu gunakan format Rupiah (contoh: Rp 150.000).\n"
        "3. Gunakan gaya bahasa Bahasa Indonesia yang profesional, ramah, dan ringkas (gunakan emoji secukupnya).\n"
        "4. Jika pengguna hanya menyapa atau mengobrol santai, jawab dengan sopan dan tawarkan bantuan terkait pencatatan transaksi."
    )

    models_to_try = ["gemini-3-flash-preview", "gemini-2.5-flash", "gemini-2.5-pro"]
    headers = {"Content-Type": "application/json"}
    contents = [
        {"role": "user", "parts": [{"text": f"System context:\n{system_instruction}\n\nPertanyaan pengguna:\n{user_text}"}]}
    ]

    for m in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
        try:
            res = requests.post(url, headers=headers, json={"contents": contents}, timeout=25)
            if res.status_code == 200:
                data = res.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "").strip()
            elif res.status_code == 401:
                return "⚠️ API Key Gemini belum valid atau kedaluwarsa. Mohon periksa kembali di menu Pengaturan."
        except Exception:
            continue
    return "Maaf, saya sedang mengalami kendala saat menghubungkan ke AI. Mohon coba sesaat lagi."

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
            
    api_key = cfg.get("gemini_api_key", "").strip() or os.environ.get("GEMINI_API_KEY", "").strip()
    webhook_url = cfg.get("google_sheets_webhook_url", "").strip() or os.environ.get("GOOGLE_SHEETS_WEBHOOK_URL", "").strip()
    
    if not token:
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    
    if not token:
        print("\n⚠️ Telegram Bot Token belum diatur di config maupun Environment Variables!")
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
                    user_text = msg["text"].strip()
                    text_cmd = user_text.lower()
                    if text_cmd in ["/start", "halo", "hi", "help"]:
                        welcome_msg = (
                            "👋 <b>Halo! Saya Asisten AI & Pencatat Pemasukan Otomatis.</b>\n\n"
                            "📸 <b>Pencatatan Otomatis:</b>\n"
                            "Kirimkan <b>foto nota, struk kwitansi, bukti transfer, atau file PDF</b> ke chat ini. Saya akan otomatis mengekstrak data transaksi, mengunggah bukti ke Google Drive, dan mencatatnya ke Google Sheets.\n\n"
                            "💬 <b>Tanya Jawab AI (Interaktif):</b>\n"
                            "Kamu juga bisa bertanya apa saja langsung di chat ini, seperti:\n"
                            "• <i>'Berapa total pemasukan bulan ini?'</i>\n"
                            "• <i>'Tampilkan rincian transaksi terakhir'</i>\n"
                            "• <i>'Berapa transfer yang masuk dari DARNIA?'</i>"
                        )
                        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": welcome_msg,
                            "parse_mode": "HTML"
                        })
                    else:
                        # Tampilkan aksi "typing" di Telegram
                        try:
                            requests.post(f"https://api.telegram.org/bot{token}/sendChatAction", json={
                                "chat_id": chat_id,
                                "action": "typing"
                            }, timeout=5)
                        except Exception:
                            pass
                            
                        # Respon via Gemini AI dengan konteks data Google Sheets
                        ai_reply = chat_with_gemini(user_text, api_key, webhook_url)
                        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": ai_reply
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
