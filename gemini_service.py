import base64
import json
import requests
from datetime import datetime

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SYSTEM_PROMPT = """
Anda adalah asisten AI akuntansi profesional ahli ekstraksi dokumen keuangan, khusus menangani DOKUMEN PEMASUKAN (Sales Invoice, Faktur Penjualan, Bukti Penerimaan Pembayaran, Kwitansi Masuk, Bukti Transfer).

Tugas Anda adalah membaca dokumen (gambar atau PDF) dan mengekstrak data transaksi pemasukan menjadi format JSON terstruktur yang presisi.

Perhatikan instruksi penting berikut:
1. FOKUS PEMASUKAN: Cari siapa pembeli/klien yang membayar uang, dan berapa nominal uang yang masuk ke kas/rekening.
2. DETEKSI NAMA & INISIAL KLIEN:
   - Identifikasi siapa 'Customer / Klien / Pembeli / Pengirim Dana'.
   - Jika nama pembeli HANYA BERUPA INISIAL atau SINGKATAN (misal: "FA", "Bpk. A", "PT. XYZ", "CS"), isi kolom `customer_initials` dengan inisial tersebut, dan set `is_initial` = true.
   - Jika nama tidak tertulis secara eksplisit, periksa keterangan/berita transfer/deskripsi untuk menyimpulkan nama pembeli.
   - Jika benar-benar tidak ada nama sama sekali, isi `customer_name` dengan "Pelanggan Umum".
3. NOMINAL UANG:
   - Ambil angka murni tanpa titik/koma pemisah ribuan (contoh: 15000000 bukan 15.000.000).
   - Pastikan `total_amount` adalah grand total (total akhir uang yang diterima/ditagihkan).
4. TANGGAL: Format selalu YYYY-MM-DD. Jika tanggal di dokumen tidak memiliki tahun, gunakan tahun sekarang ({current_year}).

OUTPUT WAJIB FORMAT JSON VALID dengan struktur persis seperti ini:
{
  "invoice_number": "string (nomor faktur / no referensi transfer)",
  "invoice_date": "YYYY-MM-DD",
  "customer_name": "string (nama klien/pembeli)",
  "customer_initials": "string (jika nama berupa inisial/singkatan, kosongkan jika nama lengkap)",
  "is_initial": true/false,
  "description": "string (ringkasan layanan atau barang yang dijual)",
  "category": "Jasa Layanan | Penjualan Produk | Retainer Bulanan | Termin / DP | Konsultasi | Lainnya",
  "subtotal": 0,
  "tax": 0,
  "discount": 0,
  "total_amount": 0,
  "payment_method": "BCA | Mandiri | BNI | BRI | QRIS | Tunai | Bank Lain",
  "status": "Lunas | Menunggu Pembayaran | DP",
  "notes": "string (catatan tambahan jika ada)",
  "line_items": [
    {
      "description": "string",
      "qty": 1,
      "unit_price": 0,
      "total": 0
    }
  ]
}
"""

def extract_invoice_data(file_bytes: bytes, mime_type: str, api_key: str, model_name: str = "gemini-3-flash-preview") -> dict:
    if not api_key:
        raise ValueError("Gemini API Key belum diisi! Silakan masukkan API Key di menu Pengaturan.")
        
    current_year = datetime.now().year
    prompt_text = SYSTEM_PROMPT.replace("{current_year}", str(current_year))
    
    b64_data = base64.b64encode(file_bytes).decode("utf-8")
    
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": b64_data
                        }
                    },
                    {
                        "text": prompt_text
                    }
                ]
            }
        ],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.1
        }
    }
    
    # Model yang aktif dan kompatibel
    models_to_try = [model_name, "gemini-3-flash-preview", "gemini-2.5-flash", "gemini-2.5-pro"]
    # prioritaskan gemini-3-flash-preview jika model default kena rate limit
    if "gemini-3-flash-preview" not in models_to_try:
        models_to_try.insert(0, "gemini-3-flash-preview")
    # hilangkan duplikasi urutan
    seen = set()
    models_to_try = [m for m in models_to_try if not (m in seen or seen.add(m))]
    
    last_err = None
    for model in models_to_try:
        url = f"{GEMINI_API_URL.format(model=model)}?key={api_key}"
        try:
            resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=45)
            if resp.status_code == 200:
                result_json = resp.json()
                text_content = result_json["candidates"][0]["content"]["parts"][0]["text"]
                parsed_data = json.loads(text_content)
                parsed_data["_model_used"] = model
                return parsed_data
            else:
                last_err = f"Status {resp.status_code}: {resp.text}"
                print(f"[GeminiService] Model {model} gagal: {last_err}")
        except Exception as e:
            last_err = str(e)
            print(f"[GeminiService] Request error dengan model {model}: {e}")
            
    raise RuntimeError(f"Gagal mengekstrak dokumen dengan Gemini API: {last_err}")
