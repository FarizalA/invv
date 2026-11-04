# 💰 Invoice Income AI - Auto Google Sheets, Google Drive & Instant Notifier

Aplikasi Web modern untuk membaca dan mencatat transaksi **PEMASUKAN** (Sales Invoice, Faktur Penjualan, Bukti Transfer Masuk, Kwitansi Pembayaran) dari format **PDF maupun Foto/Kamera HP**:
- Mengunggah file bukti fisik/PDF langsung ke folder **Google Drive** secara otomatis.
- Menyimpan link Google Drive yang dapat diklik ke dalam baris **Google Sheets**.
- Mencocokkan dengan data invoice yang sudah ada sebelumnya (mencegah duplikasi).
- Menyediakan input manual 100% fleksibel (dengan atau tanpa file).
- Mengirimkan **notifikasi otomatis ke Telegram / WhatsApp** beserta link bukti dokumennya.

---

## 🌟 Fitur Baru & Unggulan

1. **Auto-Upload File Bukti ke Google Drive**:
   - Setiap kali Anda mengunggah PDF, scan faktur, atau foto bukti transfer, file akan otomatis diunggah ke folder Google Drive (`"Bukti Pemasukan Invoice"`).
   - Izin sharing diatur agar dapat dilihat oleh siapa saja yang memiliki link.
   - Link Google Drive langsung tercatat di kolom Google Sheets (`Link Bukti (Drive)`) sebagai tautan klik-langsung `=HYPERLINK()`.

2. **Pencocokan Data & Anti-Duplikasi (*Smart Matching*)**:
   - Sistem membaca nomor invoice/referensi yang sudah tercatat di Google Sheets.
   - Jika nomor invoice yang diunggah/diketik sudah pernah dicatat sebelumnya, muncul peringatan instan:  
     `⚠️ Perhatian: No. Invoice ini sudah pernah dicatat sebelumnya atas nama [Nama Klien]`.

3. **Input Manual Fleksibel (Tanpa File)**:
   - Ada opsi tombol **"Input Manual Tanpa File"** jika menerima uang tunai / transaksi tanpa nota fisik.
   - Semua kolom (No. Invoice, Tanggal, Nama Klien, Kategori, Nominal, Bank, Status, Catatan) 100% dapat diedit secara bebas.

4. **Kamus Klien Cerdas (Auto-Enrich Inisial)**:
   - Jika di invoice cuma ada inisial seperti `FA` atau `MBP`, AI dan kamus sistem langsung mengubahnya menjadi nama panjang (misal: *Fariz Abidin* atau *PT Maju Bersama Perkasa*).
   - Otomatis mempelajari inisial baru saat Anda mengetik nama lengkap di form.

5. **Notifikasi WhatsApp & Telegram Real-time**:
   - Begitu transaksi berhasil disimpan, ringkasan transaksi beserta **Link Google Drive Dokumen Bukti** langsung dikirim ke Telegram atau WhatsApp Anda.

---

## 🚀 Cara Menjalankan

Cukup klik ganda file **`run.bat`**, lalu buka browser di:
👉 **`http://localhost:5000`**

---

## 📋 Setup 1 Menit (Google Sheets + Google Drive)

1. Buka spreadsheet Google Anda.
2. Klik menu **Ekstensi (Extensions) > Apps Script**.
3. Salin isi file `google_apps_script/Code.gs` (atau buka tab **Panduan Sheets & Drive** di web app kita) dan tempel di editor Apps Script.
4. Klik **Deploy > New deployment**:
   - Jenis: **Web app**.
   - *Execute as*: **Me (Saya)**.
   - *Who has access*: **Anyone (Siapa saja)**.
5. Klik **Deploy**, izinkan akses Drive & Sheets, lalu salin **Web App URL**.
6. Tempelkan URL tersebut di menu **Pengaturan** web app kita. Selesai!
