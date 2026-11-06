/**
 * Webhook Google Sheets & Google Drive untuk Invoice Income AI
 * Standar Akurat:
 * - doGet: Mengambil seluruh transaksi secara instan & akurat (mendukung filter tanggal, chart, dan ekspor)
 * - doPost: Mencatat invoice baru & upload file bukti transfer/PDF ke folder Google Drive
 */

function doGet(e) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getActiveSheet();
    var range = sheet.getDataRange();
    var data = range.getValues();
    var formulas = range.getFormulas();
    var richTexts = range.getRichTextValues();
    
    if (data.length <= 1) {
      return ContentService.createTextOutput("[]").setMimeType(ContentService.MimeType.JSON);
    }
    
    var result = [];
    for (var i = 1; i < data.length; i++) {
      var r = data[i];
      if (!r[1] && !r[3] && !r[9]) continue; // Lewati baris kosong
      
      var rawDate = r[2] || r[0];
      var tglISO = "";
      if (rawDate instanceof Date) {
        try {
          tglISO = Utilities.formatDate(rawDate, "Asia/Jakarta", "yyyy-MM-dd");
        } catch (e) {
          tglISO = rawDate.toISOString();
        }
      } else {
        var parsed = new Date(rawDate);
        if (!isNaN(parsed.getTime())) {
          try {
            tglISO = Utilities.formatDate(parsed, "Asia/Jakarta", "yyyy-MM-dd");
          } catch (e) {
            tglISO = parsed.toISOString();
          }
        } else {
          tglISO = String(rawDate);
        }
      }
      
      var nominalVal = Number(r[9]) || Number(r[6]) || 0;
      
      // Ekstrak URL asli Google Drive dari formula HYPERLINK atau RichText
      var driveCellVal = String(r[12] || "-");
      var formulaCell = (formulas[i] && formulas[i][12]) ? formulas[i][12] : "";
      var richLink = (richTexts[i] && richTexts[i][12]) ? richTexts[i][12].getLinkUrl() : null;
      var finalDriveUrl = "-";
      
      if (richLink && String(richLink).indexOf("http") === 0) {
        finalDriveUrl = richLink;
      } else if (formulaCell && formulaCell.indexOf("=HYPERLINK") === 0) {
        var match = formulaCell.match(/HYPERLINK\(\s*["']([^"']+)["']/i);
        if (match && match[1]) {
          finalDriveUrl = match[1];
        }
      } else if (driveCellVal && driveCellVal.indexOf("http") === 0) {
        finalDriveUrl = driveCellVal;
      }
      
      result.push({
        id: i + 1, // Baris aktual pada sheet (karena i=1 adalah baris ke-2)
        tanggal: tglISO,
        no_invoice: String(r[1] || "-"),
        nama_klien: String(r[3] || "Pelanggan Umum"),
        deskripsi: String(r[4] || "-"),
        kategori: String(r[5] || "Pemasukan"),
        subtotal: Number(r[6]) || 0,
        pajak: Number(r[7]) || 0,
        diskon: Number(r[8]) || 0,
        nominal: nominalVal,
        bank: String(r[10] || "-"),
        status: String(r[11] || "Lunas"),
        drive_url: finalDriveUrl,
        catatan: String(r[13] || "-")
      });
    }
    
    // Urutkan dari transaksi paling baru ke lama
    result.reverse();

    // Dapatkan URL folder Google Drive tempat bukti disimpan
    var driveFolderUrl = "";
    try {
      var folders = DriveApp.getFoldersByName("Bukti Pemasukan Invoice");
      if (folders.hasNext()) {
        driveFolderUrl = folders.next().getUrl();
      }
    } catch(fErr) {}

    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      spreadsheet_url: ss.getUrl(),
      drive_folder_url: driveFolderUrl,
      rows: result
    })).setMimeType(ContentService.MimeType.JSON);
    
  } catch(err) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: err.toString(),
      rows: []
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

function doPost(e) {
  var lock = LockService.getScriptLock();
  lock.tryLock(15000);
  
  try {
    var raw = e.postData.contents;
    var data = JSON.parse(raw);
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getActiveSheet();
    
    // FITUR UPDATE / EDIT TRANSAKSI
    if (data.action === "update" || data.action === "edit") {
      var invToFind = String(data.invoice_number || data.no_invoice || "").trim();
      var rowNum = Number(data.row_id || data.id || 0);
      var values = sheet.getDataRange().getValues();
      var targetRow = 0;
      
      if (rowNum >= 2 && rowNum <= sheet.getLastRow()) {
        targetRow = rowNum;
      } else if (invToFind) {
        for (var k = 1; k < values.length; k++) {
          if (String(values[k][1]).trim() === invToFind) {
            targetRow = k + 1;
            break;
          }
        }
      }
      
      if (targetRow >= 2) {
        if (data.invoice_date || data.tanggal) sheet.getRange(targetRow, 3).setValue(data.invoice_date || data.tanggal);
        if (data.customer_name || data.nama_klien) sheet.getRange(targetRow, 4).setValue(data.customer_name || data.nama_klien);
        if (data.description || data.deskripsi) sheet.getRange(targetRow, 5).setValue(data.description || data.deskripsi);
        if (data.category || data.kategori) sheet.getRange(targetRow, 6).setValue(data.category || data.kategori);
        if (data.total_amount !== undefined || data.nominal !== undefined) {
          var valNom = Number(data.total_amount !== undefined ? data.total_amount : data.nominal) || 0;
          sheet.getRange(targetRow, 10).setValue(valNom);
        }
        if (data.payment_method || data.bank) sheet.getRange(targetRow, 11).setValue(data.payment_method || data.bank);
        if (data.status) sheet.getRange(targetRow, 12).setValue(data.status);
        if (data.notes || data.catatan) sheet.getRange(targetRow, 14).setValue(data.notes || data.catatan);
        
        return ContentService.createTextOutput(JSON.stringify({
          status: "success",
          message: "Data transaksi berhasil diperbarui di baris " + targetRow,
          row: targetRow
        })).setMimeType(ContentService.MimeType.JSON);
      } else {
        return ContentService.createTextOutput(JSON.stringify({
          status: "error",
          message: "Baris transaksi dengan No. Invoice " + invToFind + " tidak ditemukan."
        })).setMimeType(ContentService.MimeType.JSON);
      }
    }
    
    // FITUR HAPUS / DELETE TRANSAKSI
    if (data.action === "delete" || data.action === "remove") {
      var invToDelete = String(data.invoice_number || data.no_invoice || "").trim();
      var rowNum = Number(data.row_id || data.id || 0);
      var values = sheet.getDataRange().getValues();
      var deletedRows = 0;
      
      // 1. Cek berdasarkan nomor baris jika valid
      if (rowNum >= 2 && rowNum <= sheet.getLastRow()) {
        var rowInv = String(values[rowNum - 1][1] || "").trim();
        // Hapus jika nomor invoice cocok atau tidak ada no_invoice pembanding
        if (!invToDelete || rowInv === invToDelete) {
          sheet.deleteRow(rowNum);
          deletedRows++;
        }
      }
      
      // 2. Jika belum terhapus (misal rowNum bergeser), cari baris berdasarkan no invoice
      if (deletedRows === 0 && invToDelete) {
        for (var k = values.length - 1; k >= 1; k--) {
          if (String(values[k][1]).trim() === invToDelete) {
            sheet.deleteRow(k + 1);
            deletedRows++;
            break; // Hanya hapus 1 baris yang cocok
          }
        }
      }
      
      return ContentService.createTextOutput(JSON.stringify({
        status: "success",
        message: "Berhasil menghapus " + deletedRows + " baris transaksi.",
        deleted_count: deletedRows
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // Cegah aksi lain yang tidak dikenal agar tidak menambah baris baru dengan nilai 0
    if (data.action && data.action !== "save" && data.action !== "create") {
      return ContentService.createTextOutput(JSON.stringify({
        status: "ignored",
        message: "Aksi tidak dikenali atau bukan create transaksi: " + data.action
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // Inisialisasi Header Otomatis jika sheet masih kosong
    if (sheet.getLastRow() === 0) {
      var headers = [
        "Waktu Input",
        "No. Invoice / Ref",
        "Tanggal Invoice",
        "Nama Klien / Pembeli",
        "Deskripsi / Layanan",
        "Kategori",
        "Subtotal",
        "PPN / Pajak",
        "Diskon",
        "Total Pemasukan (Rp)",
        "Bank / Rekening Tujuan",
        "Status Pembayaran",
        "Link Bukti (Drive)",
        "Catatan"
      ];
      sheet.appendRow(headers);
      var headerRange = sheet.getRange(1, 1, 1, headers.length);
      headerRange.setFontWeight("bold");
      headerRange.setBackground("#0F172A"); // Dark Slate
      headerRange.setFontColor("#38BDF8"); // Sky blue text
      headerRange.setHorizontalAlignment("center");
      sheet.setFrozenRows(1);
    }
    
    // 1. Simpan File Bukti ke Google Drive jika ada file_base64
    var driveUrl = "-";
    if (data.file_base64 && data.file_base64.length > 50) {
      try {
        var folderName = "Bukti Pemasukan Invoice";
        var folders = DriveApp.getFoldersByName(folderName);
        var folder = folders.hasNext() ? folders.next() : DriveApp.createFolder(folderName);
        
        var decoded = Utilities.base64Decode(data.file_base64);
        var safeFileName = (data.invoice_number ? data.invoice_number.replace(/[^a-zA-Z0-9_-]/g, "_") + "_" : "") + (data.file_name || "bukti.jpg");
        var blob = Utilities.newBlob(decoded, data.file_mime || "application/octet-stream", safeFileName);
        
        var driveFile = folder.createFile(blob);
        driveFile.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
        driveUrl = driveFile.getUrl();
      } catch (err) { 
        driveUrl = "Gagal upload: " + err.toString(); 
      }
    }
    
    // 2. Tulis baris baru ke Sheet
    var nowStr = Utilities.formatDate(new Date(), "Asia/Jakarta", "yyyy-MM-dd HH:mm:ss");
    var totalNominal = Number(data.total_amount) || Number(data.nominal) || 0;
    
    var newRow = [
      nowStr,
      data.invoice_number || data.no_invoice || "-",
      data.invoice_date || data.tanggal || Utilities.formatDate(new Date(), "Asia/Jakarta", "yyyy-MM-dd"),
      data.customer_name || data.nama_klien || "Pelanggan Umum",
      data.description || data.deskripsi || "-",
      data.category || data.kategori || "Pemasukan",
      Number(data.subtotal) || 0,
      Number(data.tax) || Number(data.pajak) || 0,
      Number(data.discount) || Number(data.diskon) || 0,
      totalNominal,
      data.payment_method || data.bank || "-",
      data.status || "Lunas",
      driveUrl,
      data.notes || data.catatan || "-"
    ];
    
    sheet.appendRow(newRow);
    var lastRow = sheet.getLastRow();
    
    // Format nominal angka (kolom 7 s/d 10)
    sheet.getRange(lastRow, 7, 1, 4).setNumberFormat("#,##0");
    
    // Buat formula Hyperlink jika link drive ada
    if (driveUrl.indexOf("http") === 0) {
      sheet.getRange(lastRow, 13).setFormula('=HYPERLINK("' + driveUrl + '"; "Lihat Bukti Drive")');
    }
    
    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      message: "Data pemasukan berhasil dicatat!",
      row: lastRow,
      drive_url: driveUrl
    })).setMimeType(ContentService.MimeType.JSON);
    
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: err.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  } finally {
    lock.releaseLock();
  }
}
