/**
 * Webhook Google Sheets & Google Drive untuk Invoice Income AI
 * Standar Akurat:
 * - doGet: Mengambil seluruh transaksi secara instan & akurat (mendukung filter tanggal, chart, dan ekspor)
 * - doPost: Mencatat invoice baru & upload file bukti transfer/PDF ke folder Google Drive
 */

/**
 * Helper: Ekstrak File ID Google Drive dari URL atau Formula HYPERLINK
 */
function extractDriveFileId(strVal) {
  if (!strVal) return null;
  var s = String(strVal);
  var m = s.match(/\/file\/d\/([a-zA-Z0-9_-]+)/) || s.match(/[?&]id=([a-zA-Z0-9_-]+)/);
  return (m && m[1]) ? m[1] : null;
}

/**
 * Helper: Hapus (pindahkan ke Trash) file Google Drive berdasarkan URL/Formula
 */
function trashDriveFile(urlOrFormula) {
  var fileId = extractDriveFileId(urlOrFormula);
  if (!fileId) return false;
  try {
    DriveApp.getFileById(fileId).setTrashed(true);
    return true;
  } catch (e) {
    return false;
  }
}

/**
 * Helper: Ambil URL/Formula Drive dari baris tertentu di Sheet (Kolom 13 / M)
 */
function getDriveCellFromRow(sheet, rowNum) {
  try {
    var cell = sheet.getRange(rowNum, 13);
    var formula = cell.getFormula();
    if (formula) return formula;
    var rich = cell.getRichTextValue();
    if (rich && rich.getLinkUrl()) return rich.getLinkUrl();
    return String(cell.getValue() || "");
  } catch (e) {
    return "";
  }
}

/**
 * Helper: Sinkronisasi folder "Bukti Pemasukan Invoice" agar file yang sudah tidak ada
 * di baris Google Sheets otomatis ikut terhapus (masuk ke Sampah/Trash Drive).
 */
function syncDriveFolderWithSheet(sheet) {
  var trashed = 0;
  try {
    var activeIds = {};
    var lastRow = sheet.getLastRow();
    if (lastRow >= 2) {
      var range = sheet.getRange(2, 13, lastRow - 1, 1);
      var vals = range.getValues();
      var forms = range.getFormulas();
      var richs = range.getRichTextValues();
      for (var i = 0; i < vals.length; i++) {
        var raw = "";
        if (richs[i] && richs[i][0] && richs[i][0].getLinkUrl()) {
          raw = richs[i][0].getLinkUrl();
        } else if (forms[i] && forms[i][0]) {
          raw = forms[i][0];
        } else if (vals[i] && vals[i][0]) {
          raw = String(vals[i][0]);
        }
        var fid = extractDriveFileId(raw);
        if (fid) activeIds[fid] = true;
      }
    }
    var folders = DriveApp.getFoldersByName("Bukti Pemasukan Invoice");
    while (folders.hasNext()) {
      var folder = folders.next();
      var files = folder.getFiles();
      while (files.hasNext()) {
        var f = files.next();
        if (!activeIds[f.getId()]) {
          f.setTrashed(true);
          trashed++;
        }
      }
    }
  } catch (err) {}
  return trashed;
}

function cleanupMarkedRows(sheet) {
  try {
    var lastRow = sheet.getLastRow();
    if (lastRow < 2) return;
    var vals = sheet.getDataRange().getValues();
    for (var rIdx = vals.length - 1; rIdx >= 1; rIdx--) {
      var row = vals[rIdx];
      var klien = String(row[3] || "").trim().toUpperCase();
      var desc = String(row[4] || "").trim();
      var nom = Number(row[9]) || 0;
      var stat = String(row[11] || "").trim().toUpperCase();
      var note = String(row[13] || "").trim().toUpperCase();
      if (klien === "DIHAPUS" || stat === "DIHAPUS" || note === "DELETED" || (nom === 0 && klien === "PELANGGAN UMUM" && desc === "-")) {
        var cellDrive = getDriveCellFromRow(sheet, rIdx + 1);
        trashDriveFile(cellDrive);
        sheet.deleteRow(rIdx + 1);
      }
    }
  } catch (err) {}
}

function doGet(e) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getActiveSheet();
    cleanupMarkedRows(sheet);
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

    // Dapatkan URL folder Google Drive & bersihkan file yatim (orphan) yang sudah dihapus dari Sheet
    var driveFolderUrl = "";
    try {
      syncDriveFolderWithSheet(sheet);
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
    
    // FITUR UPDATE / EDIT TRANSAKSI (Termasuk Sub-Action Delete Kompatibel)
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
      
      if (targetRow >= 2 && (data.sub_action === "delete" || String(data.status || "").toUpperCase() === "DIHAPUS")) {
        var cellDriveDel = getDriveCellFromRow(sheet, targetRow);
        trashDriveFile(cellDriveDel);
        if (data.drive_url) trashDriveFile(data.drive_url);
        sheet.deleteRow(targetRow);
        syncDriveFolderWithSheet(sheet);
        return ContentService.createTextOutput(JSON.stringify({
          status: "success",
          message: "Baris transaksi " + targetRow + " & file Drive berhasil dihapus.",
          deleted_count: 1
        })).setMimeType(ContentService.MimeType.JSON);
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
    
    // FITUR HAPUS / DELETE TRANSAKSI (+ HAPUS FILE BUKTI DI GOOGLE DRIVE)
    if (data.action === "delete" || data.action === "remove") {
      var invToDelete = String(data.invoice_number || data.no_invoice || "").trim();
      var rowNum = Number(data.row_id || data.id || 0);
      var values = sheet.getDataRange().getValues();
      var deletedRows = 0;
      var deletedFiles = 0;
      
      if (data.drive_url && trashDriveFile(data.drive_url)) {
        deletedFiles++;
      }
      
      // 1. Cek berdasarkan nomor baris jika valid
      if (rowNum >= 2 && rowNum <= sheet.getLastRow()) {
        var rowInv = String(values[rowNum - 1][1] || "").trim();
        if (!invToDelete || rowInv === invToDelete) {
          var cellDrive = getDriveCellFromRow(sheet, rowNum);
          if (trashDriveFile(cellDrive)) deletedFiles++;
          sheet.deleteRow(rowNum);
          deletedRows++;
        }
      }
      
      // 2. Jika belum terhapus (misal rowNum bergeser), cari baris berdasarkan no invoice
      if (deletedRows === 0 && invToDelete) {
        for (var k = values.length - 1; k >= 1; k--) {
          if (String(values[k][1]).trim() === invToDelete) {
            var targetRowNum = k + 1;
            var cellDrive2 = getDriveCellFromRow(sheet, targetRowNum);
            if (trashDriveFile(cellDrive2)) deletedFiles++;
            sheet.deleteRow(targetRowNum);
            deletedRows++;
            break; // Hanya hapus 1 baris yang cocok
          }
        }
      }
      
      // 3. Cari dan hapus file di folder Drive berdasarkan nama invoice jika belum terhapus lewat URL
      if (invToDelete && invToDelete !== "-") {
        try {
          var cleanInv = invToDelete.replace(/[^a-zA-Z0-9_-]/g, "");
          if (cleanInv.length >= 4) {
            var folders = DriveApp.getFoldersByName("Bukti Pemasukan Invoice");
            while (folders.hasNext()) {
              var fld = folders.next();
              var files = fld.getFiles();
              while (files.hasNext()) {
                var fl = files.next();
                var fname = fl.getName();
                if (fname.indexOf(cleanInv) !== -1 || fname.indexOf(invToDelete) !== -1) {
                  fl.setTrashed(true);
                  deletedFiles++;
                }
              }
            }
          }
        } catch(e) {}
      }

      // 4. Bersihkan juga file bukti di folder Drive yang sudah tidak memiliki baris di Sheet
      deletedFiles += syncDriveFolderWithSheet(sheet);
      
      return ContentService.createTextOutput(JSON.stringify({
        status: "success",
        message: "Berhasil menghapus " + deletedRows + " baris transaksi & " + deletedFiles + " file Drive.",
        deleted_count: deletedRows,
        deleted_files: deletedFiles
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
