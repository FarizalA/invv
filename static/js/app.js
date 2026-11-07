    lucide.createIcons();

    let currentInvoiceData = null;
    let clientsCache = {};
    let monitorRecordsCache = [];

    // Auto-Save State & Timer
    let isAutoSaveEnabled = localStorage.getItem('auto_save_enabled') === 'true';
    let autoSaveTimer = null;
    let autoSaveCountdownInterval = null;
    let autoSaveRemainingSeconds = 3;

    function initAutoSaveUI() {
      const toggle = document.getElementById('modal-auto-save-toggle');
      const track = document.getElementById('modal-auto-save-track');
      const thumb = document.getElementById('modal-auto-save-thumb');
      if (toggle) toggle.checked = isAutoSaveEnabled;
      if (track && thumb) {
        if (isAutoSaveEnabled) {
          track.className = 'w-7 h-4 bg-brandTeal rounded-full transition-colors relative';
          thumb.className = 'w-3 h-3 bg-white rounded-full absolute top-0.5 left-3.5 transition-transform shadow-xs';
        } else {
          track.className = 'w-7 h-4 bg-slate-300 rounded-full transition-colors relative';
          thumb.className = 'w-3 h-3 bg-white rounded-full absolute top-0.5 left-0.5 transition-transform shadow-xs';
        }
      }
    }

    function toggleAutoSave(enabled) {
      isAutoSaveEnabled = !!enabled;
      localStorage.setItem('auto_save_enabled', isAutoSaveEnabled ? 'true' : 'false');
      initAutoSaveUI();
      if (!isAutoSaveEnabled) {
        cancelAutoSaveCountdown();
        showToast('Simpan otomatis dinonaktifkan');
      } else {
        showToast('Simpan otomatis aktif (Hitung mundur 3 detik setelah scan AI)');
      }
    }

    function cancelAutoSaveCountdown() {
      if (autoSaveTimer) {
        clearTimeout(autoSaveTimer);
        autoSaveTimer = null;
      }
      if (autoSaveCountdownInterval) {
        clearInterval(autoSaveCountdownInterval);
        autoSaveCountdownInterval = null;
      }
      const banner = document.getElementById('auto-save-banner');
      if (banner) banner.classList.add('hidden');
    }

    function executeAutoSaveNow() {
      cancelAutoSaveCountdown();
      submitToSheetsAndNotify();
    }

    function triggerAutoSaveCountdown() {
      cancelAutoSaveCountdown();
      if (!isAutoSaveEnabled) return;

      const dupAlert = document.getElementById('duplicate-alert-box');
      if (dupAlert && !dupAlert.classList.contains('hidden')) {
        showToast('Auto-save dibatalkan karena terdeteksi potensi duplikasi invoice.');
        return;
      }

      // Langsung simpan cepat tanpa jeda lama (0.4 detik agar transisi halus)
      autoSaveRemainingSeconds = 1;
      const banner = document.getElementById('auto-save-banner');
      const secondsEl = document.getElementById('countdown-seconds');
      if (banner && secondsEl) {
        secondsEl.textContent = '⚡';
        banner.classList.remove('hidden');
        lucide.createIcons();
      }

      autoSaveTimer = setTimeout(() => {
        if (banner) banner.classList.add('hidden');
        submitToSheetsAndNotify(true);
      }, 350);
    }

    function selectBank(bankName) {
      const field = document.getElementById('field-payment-method');
      if (field) {
        field.value = bankName;
        field.focus();
      }
    }

    function selectEditBank(bankName) {
      const field = document.getElementById('edit-payment-method');
      if (field) {
        field.value = bankName;
        field.focus();
      }
    }

    let cachedDriveFolderUrl = '';
    let cachedSpreadsheetUrl = 'https://docs.google.com/spreadsheets/d/1Nsg5mKsy4OE543P1eVkn2212hVuUL-nVvg31myl-jiw/edit?usp=sharing';

    function openGoogleSheets() {
      const topLink = document.getElementById('top-sheets-link');
      const url = (topLink && topLink.href && topLink.href.startsWith('http')) ? topLink.href : (cachedSpreadsheetUrl || 'https://docs.google.com/spreadsheets');
      window.open(url, '_blank');
    }

    function openDriveStorage() {
      // Prioritaskan URL folder Drive yang dikirim dari Google Apps Script / config
      if (cachedDriveFolderUrl && cachedDriveFolderUrl.startsWith('http')) {
        window.open(cachedDriveFolderUrl, '_blank');
        return;
      }
      // Jika belum ada URL folder langsung, buka pencarian nama folder bukti di Google Drive
      window.open('https://drive.google.com/drive/search?q=%22Bukti%20Pemasukan%20Invoice%22', '_blank');
    }

    function viewInvoiceProof(invNum) {
      const rec = (monitorRecordsCache || []).find(r => String(r.invoice_number) === String(invNum));
      if (!rec) {
        showToast('Data transaksi tidak ditemukan.');
        return;
      }

      document.getElementById('proof-inv-number-badge').textContent = rec.invoice_number || '-';
      document.getElementById('proof-total-amount').textContent = formatRupiahJS(rec.total_amount);
      document.getElementById('proof-date').textContent = rec.invoice_date || '-';
      document.getElementById('proof-client').textContent = rec.customer_name || 'Pelanggan Umum';
      document.getElementById('proof-bank').textContent = rec.payment_method || '-';
      document.getElementById('proof-category').textContent = rec.category || 'Pemasukan';
      document.getElementById('proof-desc').textContent = rec.description || '-';
      document.getElementById('proof-notes').textContent = rec.notes || '-';

      const iframe = document.getElementById('proof-iframe-viewer');
      const img = document.getElementById('proof-img-viewer');
      const noPrev = document.getElementById('proof-no-preview');
      const driveLink = document.getElementById('proof-drive-link');
      const filenameBadge = document.getElementById('proof-filename');

      document.getElementById('proof-btn-edit').onclick = function() {
        closeProofModal();
        openEditModal(rec.invoice_number);
      };

      if (rec.drive_url && rec.drive_url.startsWith('http')) {
        driveLink.href = rec.drive_url;
        driveLink.classList.remove('hidden');
        noPrev.classList.add('hidden');

        let embedUrl = rec.drive_url;
        if (embedUrl.includes('drive.google.com/file/d/')) {
          embedUrl = embedUrl.replace(/\/view(\?.*)?$/, '/preview');
          iframe.src = embedUrl;
          iframe.classList.remove('hidden');
          img.classList.add('hidden');
          filenameBadge.textContent = 'Google Drive Document (Gambar / PDF)';
        } else if (embedUrl.match(/\.(jpeg|jpg|gif|png|webp)($|\?)/i)) {
          img.src = embedUrl;
          img.classList.remove('hidden');
          iframe.classList.add('hidden');
          filenameBadge.textContent = 'Gambar Bukti';
        } else {
          iframe.src = embedUrl;
          iframe.classList.remove('hidden');
          img.classList.add('hidden');
          filenameBadge.textContent = 'Dokumen Bukti';
        }
      } else {
        iframe.src = 'about:blank';
        iframe.classList.add('hidden');
        img.src = '';
        img.classList.add('hidden');
        noPrev.classList.remove('hidden');
        driveLink.classList.add('hidden');
        filenameBadge.textContent = 'Tidak Ada Bukti File (Input Manual)';
      }

      document.getElementById('proof-modal').classList.remove('hidden');
    }

    function closeProofModal() {
      const modal = document.getElementById('proof-modal');
      if (modal) modal.classList.add('hidden');
      const iframe = document.getElementById('proof-iframe-viewer');
      if (iframe) iframe.src = 'about:blank';
    }

    function filterByClient(clientName) {
      switchNavTab('transactions');
      const searchInput = document.getElementById('global-search-input');
      if (searchInput) {
        searchInput.value = clientName;
      }
      handleGlobalSearch(clientName);
      showToast(`Menampilkan invoice untuk klien: ${clientName}`);
    }

    // SPA Navigation Switcher
    function switchNavTab(tabName) {
      document.querySelectorAll('.tab-view').forEach(v => v.classList.remove('active'));
      document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

      const activeView = document.getElementById(`tab-view-${tabName}`);
      const activeBtn = document.getElementById(`nav-btn-${tabName}`);

      if (activeView) activeView.classList.add('active');
      if (activeBtn) activeBtn.classList.add('active');

      if (tabName === 'transactions') renderTransactionsTable(monitorRecordsCache);
      if (tabName === 'clients') loadClients();
      if (tabName === 'settings') loadSettings();
    }

    // Toast
    let toastTimer;
    function showToast(msg) {
      const toast = document.getElementById('toast-msg');
      const toastText = document.getElementById('toast-text');
      toastText.textContent = msg;
      toast.classList.add('show');
      clearTimeout(toastTimer);
      toastTimer = setTimeout(() => {
        toast.classList.remove('show');
      }, 3000);
    }

    function formatRupiahJS(val) {
      const num = parseFloat(val) || 0;
      return 'Rp ' + num.toLocaleString('id-ID');
    }

    // Modal Scan
    function triggerScanModal() {
      cancelAutoSaveCountdown();
      document.getElementById('modal-upload-zone').classList.remove('hidden');
      document.getElementById('modal-loading').classList.add('hidden');
      document.getElementById('modal-verify-form').classList.add('hidden');
      document.getElementById('scan-modal').classList.remove('hidden');
      initAutoSaveUI();
    }

    function closeScanModal() {
      cancelAutoSaveCountdown();
      document.getElementById('scan-modal').classList.add('hidden');
    }

    function handleGlobalFileSelect(e) {
      const files = Array.from(e.target.files);
      if (files.length > 0) {
        processUploadedFile(files[0]);
      }
    }

    async function processUploadedFile(file) {
      triggerScanModal();
      document.getElementById('modal-upload-zone').classList.add('hidden');
      document.getElementById('modal-loading').classList.remove('hidden');

      const formData = new FormData();
      formData.append('file', file);

      try {
        const resp = await fetch('/api/extract', {
          method: 'POST',
          body: formData
        });
        const res = await resp.json();
        document.getElementById('modal-loading').classList.add('hidden');

        if (!res.success) {
          showToast(res.message || 'Gagal mengekstrak invoice');
          document.getElementById('modal-upload-zone').classList.remove('hidden');
          return;
        }

        currentInvoiceData = res.data;
        populateModalForm(res.data);
        showToast('Dokumen berhasil diekstrak oleh AI!');
      } catch (err) {
        document.getElementById('modal-loading').classList.add('hidden');
        document.getElementById('modal-upload-zone').classList.remove('hidden');
        showToast('Error koneksi: ' + err.message);
      }
    }

    function startManualInput() {
      currentInvoiceData = {
        invoice_number: 'INV-' + new Date().toISOString().slice(2,10).replace(/-/g, '') + '-' + Math.floor(100 + Math.random() * 900),
        invoice_date: new Date().toISOString().split('T')[0],
        customer_name: '',
        address: '',
        description: 'Jasa Layanan',
        category: 'Jasa Layanan',
        subtotal: 0,
        tax: 0,
        discount: 0,
        total_amount: 0,
        payment_method: 'BCA',
        status: 'Lunas',
        notes: '',
        is_manual: true
      };
      triggerScanModal();
      populateModalForm(currentInvoiceData);
    }

    function populateModalForm(data) {
      document.getElementById('modal-upload-zone').classList.add('hidden');
      document.getElementById('modal-loading').classList.add('hidden');
      document.getElementById('modal-verify-form').classList.remove('hidden');

      const pdfViewer = document.getElementById('modal-pdf-viewer');
      const imgViewer = document.getElementById('modal-image-viewer');
      const noPreview = document.getElementById('modal-no-preview');

      if (data.is_manual || !data.file_url) {
        pdfViewer.classList.add('hidden');
        imgViewer.classList.add('hidden');
        noPreview.classList.remove('hidden');
        document.getElementById('modal-preview-filename').textContent = 'Input Manual (Tanpa Lampiran)';
      } else {
        noPreview.classList.add('hidden');
        document.getElementById('modal-preview-filename').textContent = data.file_name || 'Bukti Dokumen';

        if (data.is_pdf) {
          pdfViewer.src = data.file_url;
          pdfViewer.classList.remove('hidden');
          imgViewer.classList.add('hidden');
        } else {
          imgViewer.src = data.file_url;
          imgViewer.classList.remove('hidden');
          pdfViewer.classList.add('hidden');
        }
      }

      const alertBox = document.getElementById('initial-alert-box');
      const enrichment = data.client_enrichment || {};
      const rawInitialInput = document.getElementById('raw-initial');
      if (rawInitialInput) {
        rawInitialInput.value = data.customer_initials || enrichment.raw_name || '';
      }

      if (alertBox) {
        if (enrichment.is_resolved_from_alias) {
          alertBox.className = 'p-2.5 rounded-xl text-xs flex items-center justify-between border bg-emerald-50 text-emerald-800 border-emerald-200';
          alertBox.innerHTML = `
            <div class="flex items-center gap-2">
              <i data-lucide="check-circle" class="w-4 h-4 text-emerald-600"></i>
              <span>Inisial <b>"${enrichment.matched_alias}"</b> otomatis dicocokkan &amp; dilengkapi menjadi <b>"${enrichment.customer_name}"</b> dari kamus klien.</span>
            </div>
            <span class="text-[10px] bg-emerald-200 text-emerald-900 px-2 py-0.5 rounded-full font-bold">Auto-Enriched</span>
          `;
          alertBox.classList.remove('hidden');
        } else if (enrichment.is_potential_initial) {
          alertBox.className = 'p-2.5 rounded-xl text-xs flex items-center justify-between border bg-amber-50 text-amber-800 border-amber-200';
          alertBox.innerHTML = `
            <div class="flex items-center gap-2">
              <i data-lucide="info" class="w-4 h-4 text-amber-600"></i>
              <span>Nama terdeteksi inisial <b>"${enrichment.raw_name}"</b>. Ubah ke nama lengkap untuk disimpan ke kamus klien.</span>
            </div>
          `;
          alertBox.classList.remove('hidden');
        } else {
          alertBox.classList.add('hidden');
        }
      }

      document.getElementById('field-invoice-number').value = data.invoice_number || '';
      document.getElementById('field-invoice-date').value = data.invoice_date || data.date || new Date().toISOString().split('T')[0];
      document.getElementById('field-customer-name').value = data.customer_name || '';
      document.getElementById('field-address').value = data.address || '';
      document.getElementById('field-description').value = data.description || '';
      document.getElementById('field-category').value = data.category || 'Jasa Layanan';
      document.getElementById('field-payment-method').value = data.payment_method || data.bank_name || 'BCA';
      document.getElementById('field-subtotal').value = data.subtotal || 0;
      document.getElementById('field-tax').value = data.tax || 0;
      document.getElementById('field-discount').value = data.discount || 0;
      document.getElementById('field-total-amount').value = data.total_amount || 0;
      document.getElementById('field-status').value = data.status || 'Lunas';
      document.getElementById('field-notes').value = data.notes || '';
      document.getElementById('stored-filename').value = data.stored_filename || '';
      document.getElementById('file-mime').value = data.file_mime || '';

      updateRupiahPreview();
      checkDuplicateInvoiceNumber(data.invoice_number);

      lucide.createIcons();

      // Hitung mundur Auto-Save bila bukan input manual
      if (!data.is_manual && isAutoSaveEnabled) {
        triggerAutoSaveCountdown();
      }
    }

    function checkDuplicateInvoiceNumber(val) {
      const alertBox = document.getElementById('duplicate-alert-box');
      if (!alertBox) return;
      if (!val || !monitorRecordsCache || monitorRecordsCache.length === 0) {
        alertBox.classList.add('hidden');
        return;
      }

      const cleanVal = val.trim().toLowerCase();
      const match = monitorRecordsCache.find(x => x.invoice_number && x.invoice_number.trim().toLowerCase() === cleanVal);

      if (match) {
        document.getElementById('duplicate-alert-text').textContent = `Perhatian: No. Invoice "${val}" sudah pernah tercatat sebelumnya atas nama "${match.customer_name || '-'}"!`;
        alertBox.classList.remove('hidden');
      } else {
        alertBox.classList.add('hidden');
      }
    }

    function calculateTotal() {
      const subtotal = parseFloat(document.getElementById('field-subtotal').value) || 0;
      const tax = parseFloat(document.getElementById('field-tax').value) || 0;
      const discount = parseFloat(document.getElementById('field-discount').value) || 0;
      const total = subtotal + tax - discount;
      document.getElementById('field-total-amount').value = total > 0 ? total : subtotal;
      updateRupiahPreview();
    }

    function updateRupiahPreview() {
      const val = parseFloat(document.getElementById('field-total-amount').value) || 0;
      document.getElementById('rupiah-preview').textContent = formatRupiahJS(val);
    }

    function onClientNameInput(name) {
      const matchKey = Object.keys(clientsCache).find(k => k.toLowerCase() === name.trim().toLowerCase());
      if (matchKey) {
        document.getElementById('field-customer-name').value = clientsCache[matchKey];
        const rawEl = document.getElementById('raw-initial');
        if (rawEl) rawEl.value = matchKey;
        showToast(`Inisial "${matchKey}" dicocokkan otomatis`);
      }
    }

    // Submit to Sheets & Drive (Instan & Optimistic UI)
    async function submitToSheetsAndNotify(isAuto = false) {
      cancelAutoSaveCountdown();
      const btn = document.getElementById('btn-modal-submit');
      const origText = btn ? btn.innerHTML : '';

      const payload = {
        invoice_number: document.getElementById('field-invoice-number').value || '-',
        invoice_date: document.getElementById('field-invoice-date').value || new Date().toISOString().split('T')[0],
        customer_name: document.getElementById('field-customer-name').value || 'Pelanggan Umum',
        address: document.getElementById('field-address').value || '-',
        description: document.getElementById('field-description').value || '-',
        category: document.getElementById('field-category').value || 'Jasa Layanan',
        payment_method: document.getElementById('field-payment-method').value || 'BCA',
        subtotal: parseFloat(document.getElementById('field-subtotal').value) || 0,
        tax: parseFloat(document.getElementById('field-tax').value) || 0,
        discount: parseFloat(document.getElementById('field-discount').value) || 0,
        total_amount: parseFloat(document.getElementById('field-total-amount').value) || 0,
        status: document.getElementById('field-status').value || 'Lunas',
        notes: document.getElementById('field-notes').value || '',
        stored_filename: document.getElementById('stored-filename').value,
        file_mime: document.getElementById('file-mime').value,
        file_name: currentInvoiceData ? currentInvoiceData.file_name : '',
        file_data_url: (currentInvoiceData && currentInvoiceData.file_url && String(currentInvoiceData.file_url).startsWith('data:')) ? currentInvoiceData.file_url : '',
        raw_initial: (document.getElementById('raw-initial') || {}).value || '',
        customer_initials: (document.getElementById('raw-initial') || {}).value || ''
      };

      // Kumpulkan nilai kolom kustom dari modal
      const scanCustomInputs = document.querySelectorAll('#scan-custom-fields-container [data-scan-custom-key]');
      scanCustomInputs.forEach(inp => {
        const k = inp.getAttribute('data-scan-custom-key');
        payload[k] = inp.value;
      });

      // Optimistic UI: langsung tutup modal & tampilkan di tabel tanpa menunggu upload Drive selesai
      const tempId = Date.now();
      const optimisticRow = {
        id: tempId,
        invoice_number: payload.invoice_number,
        customer_name: payload.customer_name,
        address: payload.address,
        invoice_date: payload.invoice_date,
        description: payload.description,
        category: payload.category,
        total_amount: payload.total_amount,
        payment_method: payload.payment_method,
        status: payload.status,
        drive_url: (currentInvoiceData && currentInvoiceData.file_url) ? currentInvoiceData.file_url : '-'
      };

      if (!Array.isArray(monitorRecordsCache)) monitorRecordsCache = [];
      monitorRecordsCache.unshift(optimisticRow);
      renderDashboardStats(monitorRecordsCache);
      renderRecentInvoices(monitorRecordsCache);
      renderTopClients(monitorRecordsCache);
      renderTransactionsTable(monitorRecordsCache);
      const sbCount = document.getElementById('sidebar-tx-count');
      if (sbCount) sbCount.textContent = monitorRecordsCache.length;

      closeScanModal();
      showToast(isAuto ? '⚡ Auto-Save: Menyimpan ke Sheets & Drive...' : '⚡ Menyimpan transaksi...');

      window._activeSaves = window._activeSaves || {};
      window._deletedTempIds = window._deletedTempIds || new Set();
      let resolveSavePromise;
      window._activeSaves[tempId] = new Promise(resolve => { resolveSavePromise = resolve; });

      try {
        const resp = await fetch('/api/save', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(payload)
        });
        const res = await resp.json();
        if (resolveSavePromise) resolveSavePromise({ row_id: res.row, drive_url: res.drive_url });
        delete window._activeSaves[tempId];

        if (window._deletedTempIds.has(tempId)) {
          return;
        }

        if (res.success) {
          // Perbarui id baris & link drive asli dari respons server
          const targetIdx = monitorRecordsCache.findIndex(r => r.id === tempId);
          if (targetIdx !== -1) {
            if (res.row) monitorRecordsCache[targetIdx].id = res.row;
            if (res.drive_url && res.drive_url !== '-') monitorRecordsCache[targetIdx].drive_url = res.drive_url;
            renderRecentInvoices(monitorRecordsCache);
            renderTransactionsTable(monitorRecordsCache);
          }
          showToast('✅ Berhasil disimpan ke Google Sheets & Drive!');
          setTimeout(() => loadMonitorRecords(true), 500);
        } else {
          monitorRecordsCache = monitorRecordsCache.filter(r => r.id !== tempId);
          renderDashboardStats(monitorRecordsCache);
          renderRecentInvoices(monitorRecordsCache);
          renderTopClients(monitorRecordsCache);
          renderTransactionsTable(monitorRecordsCache);
          showToast('❌ Gagal: ' + res.message);
        }
      } catch (err) {
        if (resolveSavePromise) resolveSavePromise({});
        if (window._activeSaves) delete window._activeSaves[tempId];
        monitorRecordsCache = monitorRecordsCache.filter(r => r.id !== tempId);
        renderDashboardStats(monitorRecordsCache);
        renderRecentInvoices(monitorRecordsCache);
        renderTopClients(monitorRecordsCache);
        renderTransactionsTable(monitorRecordsCache);
        showToast('Error: ' + err.message);
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = origText;
          lucide.createIcons();
        }
      }
    }

    // Monitor Records & Render
    async function loadMonitorRecords(isForce = false) {
      const refreshIcon = document.getElementById('top-refresh-icon');
      if (refreshIcon) refreshIcon.classList.add('animate-spin');

      try {
        const url = isForce ? '/api/records?force=1' : '/api/records';
        const resp = await fetch(url);
        const res = await resp.json();
        if (res.success && res.rows) {
          monitorRecordsCache = res.rows;
          if (res.drive_folder_url) {
            cachedDriveFolderUrl = res.drive_folder_url;
          }
          renderDashboardStats(res.rows);
          renderRecentInvoices(res.rows);
          renderTopClients(res.rows);
          renderTransactionsTable(res.rows);

          if (res.spreadsheet_url) {
            cachedSpreadsheetUrl = res.spreadsheet_url;
            const topLink = document.getElementById('top-sheets-link');
            if (topLink) topLink.href = res.spreadsheet_url;
          }

          document.getElementById('sidebar-tx-count').textContent = res.rows.length;
        }
      } catch (e) {
        console.error('Error fetching records:', e);
      } finally {
        if (refreshIcon) refreshIcon.classList.remove('animate-spin');
      }
    }

    function renderDashboardStats(records) {
      let totalAmount = 0;
      let paidCount = 0;
      const clientSet = new Set();

      records.forEach(r => {
        totalAmount += parseFloat(r.total_amount) || 0;
        if ((r.status || '').toLowerCase().includes('lunas')) paidCount++;
        if (r.customer_name && r.customer_name !== '-') clientSet.add(r.customer_name);
      });

      document.getElementById('hero-total-amount').textContent = formatRupiahJS(totalAmount);
      document.getElementById('hero-total-count').textContent = `${records.length} Dokumen`;
      document.getElementById('hero-paid-count').textContent = `${paidCount} Lunas`;
      const miniClientEl = document.getElementById('mini-client-count');
      if (miniClientEl) miniClientEl.textContent = clientSet.size;

      renderMonthlyRevenueChart(records);
    }

    function formatCompactRupiah(num) {
      if (!num || num <= 0) return '0';
      if (num >= 1000000000) return (num / 1000000000).toFixed(1).replace('.0', '') + 'M';
      if (num >= 1000000) return (num / 1000000).toFixed(1).replace('.0', '') + 'Jt';
      if (num >= 1000) return (num / 1000).toFixed(1).replace('.0', '') + 'Rb';
      return Math.round(num).toString();
    }

    function renderMonthlyRevenueChart(records) {
      const container = document.getElementById('monthly-chart-container');
      const subtitle = document.getElementById('monthly-chart-subtitle');
      if (!container) return;

      const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];
      const now = new Date();
      const months = [];

      for (let i = 5; i >= 0; i--) {
        const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        months.push({
          key: `${y}-${m}`,
          label: monthNames[d.getMonth()],
          total: 0
        });
      }

      (records || []).forEach(r => {
        const rawDate = String(r.invoice_date || r.date || r.tanggal || '').trim();
        let monthKey = '';
        if (/^\d{4}-\d{2}/.test(rawDate)) {
          monthKey = rawDate.slice(0, 7);
        } else if (/^\d{1,2}\/\d{1,2}\/\d{4}/.test(rawDate)) {
          const parts = rawDate.split('/');
          monthKey = `${parts[2]}-${parts[1].padStart(2, '0')}`;
        }
        if (monthKey) {
          const found = months.find(m => m.key === monthKey);
          if (found) {
            found.total += (parseFloat(r.total_amount) || 0);
          }
        }
      });

      const maxVal = Math.max(...months.map(m => m.total), 0);
      const currentMonthTotal = months[months.length - 1].total;
      const total6Months = months.reduce((acc, m) => acc + m.total, 0);

      if (subtitle) {
        if (total6Months > 0) {
          subtitle.textContent = `Bulan ini: ${formatRupiahJS(currentMonthTotal)} • 6 Bln: ${formatCompactRupiah(total6Months)}`;
        } else {
          subtitle.textContent = 'Belum ada transaksi di 6 bulan terakhir';
        }
      }

      let ceiling = 10000000;
      if (maxVal > 0) {
        const mag = Math.pow(10, Math.floor(Math.log10(maxVal)));
        const norm = maxVal / mag;
        let mult = 10;
        if (norm <= 1.2) mult = 1.2;
        else if (norm <= 2) mult = 2.0;
        else if (norm <= 2.5) mult = 2.5;
        else if (norm <= 5) mult = 5.0;
        ceiling = Math.max(mult * mag, 100000);
      }

      const yTop = 14;
      const yBottom = 76;
      const yMid = 45;

      const topLabel = formatCompactRupiah(ceiling);
      const midLabel = formatCompactRupiah(ceiling / 2);
      const bottomLabel = '0';

      const xStart = 32;
      const xEnd = 252;
      const xStep = (xEnd - xStart) / 5;

      const points = months.map((m, idx) => {
        const x = xStart + (idx * xStep);
        const ratio = ceiling > 0 ? (m.total / ceiling) : 0;
        const clampedRatio = Math.min(Math.max(ratio, 0), 1);
        const y = yBottom - (clampedRatio * (yBottom - yTop));
        return { x: Math.round(x * 10) / 10, y: Math.round(y * 10) / 10, data: m };
      });

      let pathD = `M ${points[0].x} ${points[0].y}`;
      for (let i = 0; i < points.length - 1; i++) {
        const p0 = points[i === 0 ? 0 : i - 1];
        const p1 = points[i];
        const p2 = points[i + 1];
        const p3 = points[i + 1 >= points.length - 1 ? points.length - 1 : i + 2];
        const cp1x = (p1.x + (p2.x - p0.x) / 6).toFixed(1);
        const cp1y = (p1.y + (p2.y - p0.y) / 6).toFixed(1);
        const cp2x = (p2.x - (p3.x - p1.x) / 6).toFixed(1);
        const cp2y = (p2.y - (p3.y - p1.y) / 6).toFixed(1);
        pathD += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2.x} ${p2.y}`;
      }

      const areaD = `${pathD} L ${points[points.length - 1].x} ${yBottom} L ${points[0].x} ${yBottom} Z`;

      let peakIdx = points.length - 1;
      if (maxVal > 0) {
        let highest = -1;
        points.forEach((p, idx) => {
          if (p.data.total > highest) {
            highest = p.data.total;
            peakIdx = idx;
          }
        });
      }

      let circlesSvg = '';
      let monthLabelsSvg = '';

      points.forEach((p, idx) => {
        const isPeak = (idx === peakIdx && p.data.total > 0);
        if (isPeak) {
          circlesSvg += `
            <circle cx="${p.x}" cy="${p.y}" r="4.5" fill="#f6c32e" stroke="#ffffff" stroke-width="1.8">
              <title>${p.data.label}: ${formatRupiahJS(p.data.total)}</title>
            </circle>`;
        } else {
          circlesSvg += `
            <circle cx="${p.x}" cy="${p.y}" r="2.5" fill="#ffffff" fill-opacity="0.8">
              <title>${p.data.label}: ${formatRupiahJS(p.data.total)}</title>
            </circle>`;
        }

        monthLabelsSvg += `<text x="${p.x}" y="91" text-anchor="middle">${p.data.label}</text>`;
      });

      container.innerHTML = `
        <svg viewBox="0 0 260 96" width="100%" height="100%" fill="none" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="chartGradDash" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#ffffff" stop-opacity="0.38"/>
              <stop offset="100%" stop-color="#ffffff" stop-opacity="0.0"/>
            </linearGradient>
          </defs>
          <g font-size="7.5" fill="rgba(255,255,255,0.78)" font-family="Poppins, sans-serif">
            <text x="0" y="17" text-anchor="start">${topLabel}</text>
            <line x1="${xStart - 4}" y1="${yTop}" x2="${xEnd}" y2="${yTop}" stroke="rgba(255,255,255,0.2)" stroke-dasharray="2 2"/>
            
            <text x="0" y="48" text-anchor="start">${midLabel}</text>
            <line x1="${xStart - 4}" y1="${yMid}" x2="${xEnd}" y2="${yMid}" stroke="rgba(255,255,255,0.2)" stroke-dasharray="2 2"/>
            
            <text x="0" y="79" text-anchor="start">${bottomLabel}</text>
            <line x1="${xStart - 4}" y1="${yBottom}" x2="${xEnd}" y2="${yBottom}" stroke="rgba(255,255,255,0.2)" stroke-dasharray="2 2"/>

            ${monthLabelsSvg}
          </g>
          
          <path d="${areaD}" fill="url(#chartGradDash)"/>
          <path d="${pathD}" stroke="#ffffff" stroke-width="2.2" stroke-linecap="round"/>
          ${circlesSvg}
        </svg>
      `;
    }

    function renderRecentInvoices(records) {
      const list = document.getElementById('recent-invoices-list');
      list.innerHTML = '';

      if (!records || records.length === 0) {
        list.innerHTML = '<div class="p-6 text-center text-xs text-slate-400 bg-white rounded-2xl border border-slate-100">Belum ada transaksi yang tercatat.</div>';
        return;
      }

      const colors = ['yellow', 'coral', 'teal', 'pink'];
      records.slice(0, 5).forEach((r, idx) => {
        const col = colors[idx % colors.length];
        const initial = (r.customer_name || 'U').charAt(0).toUpperCase();

        const card = document.createElement('div');
        card.className = `course-card ${idx === 1 ? 'featured' : ''}`;
        card.innerHTML = `
          <div class="flex items-center gap-3 min-w-0 cursor-pointer" onclick="viewInvoiceProof('${r.invoice_number}')" title="Klik untuk lihat bukti invoice">
            <div class="course-icon ${col}">${initial}</div>
            <div class="min-w-0">
              <h4 class="text-xs font-semibold text-brandDark truncate hover:text-brandTeal">${r.customer_name || 'Pelanggan'}</h4>
              <p class="text-[10px] text-slate-400 font-mono">${r.invoice_number || '-'} • ${formatRupiahJS(r.total_amount)}</p>
            </div>
          </div>
          <div class="flex items-center gap-1.5">
            <button onclick="viewInvoiceProof('${r.invoice_number}')" title="Lihat Bukti Dokumen" class="px-2.5 py-1 rounded-lg text-[10px] font-semibold bg-teal-50 text-teal-700 hover:bg-brandTeal hover:text-white transition-colors">
              Bukti
            </button>
            <button onclick="openEditModal('${r.invoice_number}')" title="Edit Data" class="px-2.5 py-1 rounded-lg text-[10px] font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors">
              Edit
            </button>
            <button onclick="deleteRecordAction('${r.invoice_number}', ${r.id || 0})" title="Hapus" class="w-6 h-6 rounded-full hover:bg-rose-50 hover:text-rose-600 text-slate-400 text-xs flex items-center justify-center">
              &times;
            </button>
          </div>
        `;
        list.appendChild(card);
      });
    }

    function renderTopClients(records) {
      const container = document.getElementById('top-clients-list');
      container.innerHTML = '';

      const clientMap = {};
      records.forEach(r => {
        const name = r.customer_name || 'Umum';
        if (!clientMap[name]) clientMap[name] = { count: 0, total: 0 };
        clientMap[name].count += 1;
        clientMap[name].total += parseFloat(r.total_amount) || 0;
      });

      const sorted = Object.entries(clientMap).sort((a,b) => b[1].count - a[1].count).slice(0, 4);

      if (sorted.length === 0) {
        container.innerHTML = '<div class="p-6 text-center text-xs text-slate-400 bg-white rounded-2xl border border-slate-100">Belum ada data klien.</div>';
        return;
      }

      const avatarBgs = ['#f26b3a', '#f6b828', '#50b4a2', '#e04f44'];
      sorted.forEach(([name, val], idx) => {
        const bg = avatarBgs[idx % avatarBgs.length];
        const card = document.createElement('div');
        card.className = 'instructor-card';
        card.innerHTML = `
          <div class="flex items-center gap-3">
            <div class="instructor-avatar" style="background:${bg}; color:#fff;">
              ${name.slice(0, 2).toUpperCase()}
            </div>
            <div>
              <h4 class="text-xs font-semibold text-brandDark">${name}</h4>
              <p class="text-[10px] text-slate-400">${val.count} Transaksi • ${formatRupiahJS(val.total)}</p>
            </div>
          </div>
          <button class="btn-instructor-pill ${idx === 1 ? 'active' : ''}" onclick="filterByClient('${name.replace(/'/g, "\\'")}')" title="Lihat transaksi klien ini">
            Invoices
          </button>
        `;
        container.appendChild(card);
      });
    }


    // =======================================================
    // SISTEM DINAMIS: KUSTOMISASI KOLOM TABEL & PRESET BISNIS
    // =======================================================
    const defaultSystemColumns = [
      { key: "invoice_date", label: "Tanggal", type: "date", enabled: true, required: true, is_system: true },
      { key: "invoice_number", label: "No. Invoice / Ref", type: "text", enabled: true, required: false, is_system: true },
      { key: "customer_name", label: "Nama Klien / Pembeli", type: "text", enabled: true, required: false, is_system: true },
      { key: "description", label: "Deskripsi", type: "text", enabled: true, required: false, is_system: true },
      { key: "subtotal", label: "Subtotal", type: "currency", enabled: false, required: false, is_system: true },
      { key: "tax", label: "PPN / Pajak", type: "currency", enabled: false, required: false, is_system: true },
      { key: "discount", label: "Diskon", type: "currency", enabled: false, required: false, is_system: true },
      { key: "total_amount", label: "Total Nominal", type: "currency", enabled: true, required: true, is_system: true },
      { key: "payment_method", label: "Bank / Metode", type: "text", enabled: true, required: false, is_system: true },
      { key: "status", label: "Status", type: "badge", enabled: true, required: false, is_system: true }
    ];

    window.currentTableColumns = JSON.parse(JSON.stringify(defaultSystemColumns));

    async function loadTableColumns() {
      try {
        const resp = await fetch('/api/columns');
        const res = await resp.json();
        if (res.success && Array.isArray(res.columns) && res.columns.length > 0) {
          window.currentTableColumns = res.columns;
        }
      } catch (err) {
        console.warn('Gagal memuat kolom dari server, menggunakan default:', err);
      }
      syncModalFormFields();
      if (monitorRecordsCache && monitorRecordsCache.length) {
        renderTransactionsTable(monitorRecordsCache);
      }
    }

    function openColumnSettingsModal() {
      renderColumnSettingsList();
      const modal = document.getElementById('column-settings-modal');
      if (modal) modal.classList.remove('hidden');
      if (window.lucide) lucide.createIcons();
    }

    function closeColumnSettingsModal() {
      const modal = document.getElementById('column-settings-modal');
      if (modal) modal.classList.add('hidden');
    }

    function renderColumnSettingsList() {
      const container = document.getElementById('column-list-container');
      if (!container) return;
      container.innerHTML = '';

      const cols = window.currentTableColumns || defaultSystemColumns;
      cols.forEach((col, idx) => {
        const item = document.createElement('div');
        item.className = 'p-3 flex items-center justify-between hover:bg-slate-50 transition-colors';
        const isCore = col.key === 'total_amount' || col.key === 'invoice_date';
        const typeBadge = col.type === 'currency' ? 'Rp' : (col.type === 'date' ? 'Tgl' : 'Teks');

        item.innerHTML = `
          <div class="flex items-center gap-3">
            <input type="checkbox" id="col-check-${col.key}" ${col.enabled ? 'checked' : ''} ${isCore ? 'disabled title="Kolom inti wajib"' : ''} onchange="toggleColumnVisibility('${col.key}', this.checked)" class="w-4 h-4 rounded text-brandTeal focus:ring-brandTeal cursor-pointer">
            <div>
              <div class="flex items-center gap-2">
                <span class="font-semibold text-slate-800 text-xs">${col.label}</span>
                <span class="px-1.5 py-0.5 rounded text-[9px] font-mono bg-slate-100 text-slate-500">${typeBadge}</span>
                ${col.is_system ? '<span class="text-[9px] text-slate-400">Bawaan</span>' : '<span class="px-1.5 py-0.5 rounded text-[9px] bg-teal-50 text-teal-700 font-semibold">Kustom</span>'}
              </div>
              <span class="text-[10px] text-slate-400 font-mono">${col.key}</span>
            </div>
          </div>
          <div>
            ${!col.is_system ? `<button type="button" onclick="deleteCustomColumn('${col.key}')" class="text-rose-500 hover:text-rose-700 p-1 rounded hover:bg-rose-50 text-xs" title="Hapus kolom ini">Hapus</button>` : ''}
          </div>
        `;
        container.appendChild(item);
      });
    }

    function toggleColumnVisibility(key, isChecked) {
      const target = (window.currentTableColumns || []).find(c => c.key === key);
      if (target) {
        target.enabled = isChecked;
      }
    }

    function applyColumnPreset(presetName) {
      let cols = JSON.parse(JSON.stringify(defaultSystemColumns));
      if (presetName === 'jasa') {
        // Jasa / Freelance: Standar tanpa pajak/diskon
        cols.forEach(c => {
          if (['subtotal', 'tax', 'discount'].includes(c.key)) c.enabled = false;
          else c.enabled = true;
        });
        showToast('Preset Jasa / Freelance diterapkan.');
      } else if (presetName === 'retail') {
        // Toko / Retail: Tidak butuh No Invoice, fokus ke Klien, Item, Total
        cols.forEach(c => {
          if (['invoice_number', 'subtotal', 'tax', 'discount'].includes(c.key)) c.enabled = false;
          else c.enabled = true;
        });
        showToast('Preset Toko / Retail diterapkan.');
      } else if (presetName === 'fnb') {
        // Kafe / Resto: Kolom No Meja / Kasir
        cols.forEach(c => {
          if (['invoice_number', 'subtotal', 'tax', 'discount'].includes(c.key)) c.enabled = false;
          else c.enabled = true;
        });
        // Tambah kolom No Meja jika belum ada
        if (!cols.some(c => c.key === 'no_meja')) {
          cols.push({ key: 'no_meja', label: 'No. Meja / Area', type: 'text', enabled: true, required: false, is_system: false });
        }
        showToast('Preset Kafe / Restoran diterapkan.');
      } else if (presetName === 'lengkap') {
        // Format Lengkap: Aktifkan semua termasuk Subtotal, Pajak & Diskon
        cols.forEach(c => c.enabled = true);
        showToast('Preset Lengkap (+Pajak & Diskon) diterapkan.');
      }

      window.currentTableColumns = cols;
      renderColumnSettingsList();
    }

    function addNewCustomColumn() {
      const labelInput = document.getElementById('new-col-label');
      const typeSelect = document.getElementById('new-col-type');
      const label = (labelInput ? labelInput.value : '').trim();
      const type = typeSelect ? typeSelect.value : 'text';

      if (!label) {
        alert('Harap masukkan nama kolom!');
        return;
      }

      const key = 'custom_' + label.toLowerCase().replace(/[^a-z0-9]/g, '_').slice(0, 20);
      if ((window.currentTableColumns || []).some(c => c.key === key)) {
        alert('Kolom dengan nama serupa sudah ada!');
        return;
      }

      window.currentTableColumns.push({
        key: key,
        label: label,
        type: type,
        enabled: true,
        required: false,
        is_system: false
      });

      labelInput.value = '';
      renderColumnSettingsList();
      showToast(`Kolom "${label}" berhasil ditambahkan.`);
    }

    function deleteCustomColumn(key) {
      window.currentTableColumns = (window.currentTableColumns || []).filter(c => c.key !== key);
      renderColumnSettingsList();
      showToast('Kolom kustom berhasil dihapus.');
    }

    function resetDefaultColumns() {
      if (!confirm('Kembalikan semua pengaturan kolom ke setelan pabrik?')) return;
      window.currentTableColumns = JSON.parse(JSON.stringify(defaultSystemColumns));
      renderColumnSettingsList();
      showToast('Kolom direset ke setelan pabrik.');
    }

    async function saveColumnSettings() {
      try {
        const resp = await fetch('/api/columns', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ columns: window.currentTableColumns })
        });
        const res = await resp.json();
        if (res.success) {
          showToast('Pengaturan kolom berhasil disimpan.');
          closeColumnSettingsModal();
          syncModalFormFields();
          renderTransactionsTable(monitorRecordsCache);
        } else {
          showToast('Gagal: ' + res.message);
        }
      } catch (err) {
        showToast('Error: ' + err.message);
      }
    }

    function syncModalFormFields(prefilledData = {}) {
      const cols = window.currentTableColumns || defaultSystemColumns;

      // Visibility subtotal, tax, discount
      const hasSubtotal = cols.some(c => c.key === 'subtotal' && c.enabled);
      const hasTax = cols.some(c => c.key === 'tax' && c.enabled);
      const hasDiscount = cols.some(c => c.key === 'discount' && c.enabled);
      const wrapCalc = document.getElementById('wrap-calc-fields');
      const wrapSubtotal = document.getElementById('wrap-field-subtotal');
      const wrapTax = document.getElementById('wrap-field-tax');
      const wrapDiscount = document.getElementById('wrap-field-discount');

      if (wrapSubtotal) wrapSubtotal.style.display = hasSubtotal ? '' : 'none';
      if (wrapTax) wrapTax.style.display = hasTax ? '' : 'none';
      if (wrapDiscount) wrapDiscount.style.display = hasDiscount ? '' : 'none';
      if (wrapCalc) wrapCalc.style.display = (hasSubtotal || hasTax || hasDiscount) ? 'grid' : 'none';

      // Dynamic Custom Fields for Scan Modal
      const scanCustomContainer = document.getElementById('scan-custom-fields-container');
      if (scanCustomContainer) {
        scanCustomContainer.innerHTML = '';
        const customCols = cols.filter(c => !c.is_system && c.enabled);
        customCols.forEach(c => {
          const div = document.createElement('div');
          const inputType = c.type === 'currency' ? 'number' : (c.type === 'date' ? 'date' : 'text');
          const val = prefilledData[c.key] || '';
          div.innerHTML = `
            <label class="block text-[11px] font-semibold text-slate-600 mb-1">${c.label}</label>
            <input type="${inputType}" data-scan-custom-key="${c.key}" value="${val}" placeholder="Isi ${c.label}..." class="w-full px-3 py-1.5 text-xs border border-slate-200 rounded-xl font-medium bg-white">
          `;
          scanCustomContainer.appendChild(div);
        });
      }
    }

    function renderTransactionsTable(records) {
      const theadRow = document.getElementById('transactions-header-row');
      const tbody = document.getElementById('transactions-tbody');
      if (!tbody) return;

      const cols = (window.currentTableColumns && window.currentTableColumns.length)
        ? window.currentTableColumns
        : defaultSystemColumns;
      const activeCols = cols.filter(c => c.enabled !== false);

      // Render Dynamic Headers
      if (theadRow) {
        let thHtml = activeCols.map(c => {
          let align = 'text-left';
          if (c.type === 'currency' || c.key === 'total_amount' || c.key === 'subtotal') align = 'text-right';
          if (['payment_method', 'status', 'drive_url'].includes(c.key) || c.type === 'badge' || c.type === 'drive') align = 'text-center';
          let extraWidth = '';
          if (c.key === 'description') extraWidth = 'max-w-[170px]';
          return `<th class="px-4 py-3 ${align} ${extraWidth}">${c.label}</th>`;
        }).join('');
        thHtml += '<th class="px-4 py-3 text-center">Aksi</th>';
        theadRow.innerHTML = thHtml;
      }

      tbody.innerHTML = '';
      if (!records || records.length === 0) {
        tbody.innerHTML = `<tr><td colspan="${activeCols.length + 1}" class="text-center py-8 text-slate-400">Tidak ada transaksi ditemukan.</td></tr>`;
        return;
      }

      records.forEach(r => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-slate-50 transition-colors';

        let cellsHtml = activeCols.map(col => {
          if (col.key === 'invoice_date') {
            return `<td class="px-4 py-3 text-slate-500 font-medium whitespace-nowrap">${r.invoice_date || '-'}</td>`;
          }
          if (col.key === 'invoice_number') {
            return `<td class="px-4 py-3 font-bold font-mono text-brandDark"><span class="cursor-pointer hover:underline text-brandTeal" onclick="viewInvoiceProof('${r.invoice_number}')" title="Klik untuk lihat bukti invoice">${r.invoice_number || '-'}</span></td>`;
          }
          if (col.key === 'customer_name') {
            return `<td class="px-4 py-3 font-semibold text-slate-800 truncate max-w-[150px]" title="${(r.customer_name || '').replace(/"/g, '&quot;')}">${r.customer_name || '-'}</td>`;
          }
          if (col.key === 'description') {
            return `<td class="px-4 py-3 text-slate-600 truncate max-w-[170px]" title="${(r.description || '').replace(/"/g, '&quot;')}">${r.description || '-'}</td>`;
          }
          if (col.key === 'total_amount' || col.key === 'subtotal' || col.key === 'tax' || col.key === 'discount' || col.type === 'currency') {
            const val = parseFloat(r[col.key] || (r.custom_fields && r.custom_fields[col.key]) || 0);
            return `<td class="px-4 py-3 text-right font-mono font-bold text-brandCoral">${formatRupiahJS(val)}</td>`;
          }
          if (col.key === 'payment_method') {
            return `<td class="px-4 py-3 text-center font-medium">${r.payment_method || '-'}</td>`;
          }
          if (col.key === 'status') {
            return `<td class="px-4 py-3 text-center"><span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700">${r.status || 'Lunas'}</span></td>`;
          }
          if (col.key === 'drive_url') {
            let driveBtn = '<span class="text-slate-400 font-mono text-xs">-</span>';
            if (r.drive_url && r.drive_url.startsWith('http')) {
              driveBtn = `
                <div class="flex items-center justify-center gap-1">
                  <button onclick="viewInvoiceProof('${r.invoice_number}')" class="px-2 py-0.5 rounded-lg bg-teal-50 text-teal-700 font-bold text-[10px] hover:bg-teal-100 transition-colors" title="Lihat Pratinjau Bukti">Bukti</button>
                  <a href="${r.drive_url}" target="_blank" title="Buka di Google Drive" class="p-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-600 text-[10px] flex items-center justify-center">
                    <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                  </a>
                </div>`;
            }
            return `<td class="px-4 py-3 text-center whitespace-nowrap">${driveBtn}</td>`;
          }
          // Kolom kustom lainnya
          const customVal = (r.custom_fields && r.custom_fields[col.key] !== undefined) ? r.custom_fields[col.key] : (r[col.key] !== undefined ? r[col.key] : '-');
          return `<td class="px-4 py-3 text-slate-700 font-medium">${customVal || '-'}</td>`;
        }).join('');

        cellsHtml += `
          <td class="px-4 py-3 text-center whitespace-nowrap">
            <button onclick="viewInvoiceProof('${r.invoice_number}')" class="px-2 py-1 rounded bg-teal-50 hover:bg-teal-100 text-teal-800 font-bold text-[10px] mr-1">Bukti</button>
            <button onclick="openEditModal('${r.invoice_number}')" class="px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-[10px] mr-1">Edit</button>
            <button onclick="deleteRecordAction('${r.invoice_number}', ${r.id || 0})" class="px-2 py-1 rounded bg-rose-50 hover:bg-rose-100 text-rose-700 font-bold text-[10px]">Hapus</button>
          </td>
        `;

        tr.innerHTML = cellsHtml;
        tbody.appendChild(tr);
      });
    }

    // Global Search
    function handleGlobalSearch(query) {
      const q = query.toLowerCase().trim();
      const filtered = monitorRecordsCache.filter(r => {
        return (r.invoice_number || '').toLowerCase().includes(q) ||
               (r.customer_name || '').toLowerCase().includes(q) ||
               (r.description || '').toLowerCase().includes(q) ||
               (r.category || '').toLowerCase().includes(q);
      });

      renderRecentInvoices(filtered);
      renderTransactionsTable(filtered);
    }

    function filterRecentInvoices(category) {
      if (category === 'all') {
        renderRecentInvoices(monitorRecordsCache);
      } else {
        const filtered = monitorRecordsCache.filter(r => (r.category || '').toLowerCase() === category.toLowerCase());
        renderRecentInvoices(filtered);
      }
    }

    // Edit Transaction
    function openEditModal(invNum) {
      const rec = monitorRecordsCache.find(r => String(r.invoice_number) === String(invNum));
      if (!rec) return;

      document.getElementById('edit-row-id').value = rec.id || '';
      document.getElementById('edit-inv-number').value = rec.invoice_number || '';
      document.getElementById('edit-inv-date').value = rec.invoice_date || '';
      document.getElementById('edit-customer-name').value = rec.customer_name || '';
      document.getElementById('edit-address').value = rec.address || '';
      document.getElementById('edit-description').value = rec.description || '';
      document.getElementById('edit-category').value = rec.category || 'Jasa Layanan';
      document.getElementById('edit-total-amount').value = rec.total_amount || 0;
      document.getElementById('edit-payment-method').value = rec.payment_method || 'BCA';
      document.getElementById('edit-status').value = rec.status || 'Lunas';
      document.getElementById('edit-notes').value = rec.notes || '';

      // Render dan isi nilai kolom kustom di modal edit
      const editCustomContainer = document.getElementById('edit-custom-fields-container');
      if (editCustomContainer) {
        editCustomContainer.innerHTML = '';
        const customCols = (window.currentTableColumns || defaultSystemColumns).filter(c => !c.is_system && c.enabled);
        customCols.forEach(c => {
          const div = document.createElement('div');
          const inputType = c.type === 'currency' ? 'number' : (c.type === 'date' ? 'date' : 'text');
          const val = rec[c.key] || (rec.custom_fields && rec.custom_fields[c.key]) || '';
          div.innerHTML = `
            <label class="block text-xs font-semibold text-slate-600 mb-1">${c.label}</label>
            <input type="${inputType}" data-edit-custom-key="${c.key}" value="${val}" placeholder="Isi ${c.label}..." class="w-full px-3 py-1.5 text-xs border border-slate-200 rounded-xl font-medium bg-white">
          `;
          editCustomContainer.appendChild(div);
        });
      }

      document.getElementById('edit-modal').classList.remove('hidden');
    }

    function closeEditModal() {
      document.getElementById('edit-modal').classList.add('hidden');
    }

    async function submitEditRecord() {
      const payload = {
        row_id: document.getElementById('edit-row-id').value,
        invoice_number: document.getElementById('edit-inv-number').value,
        invoice_date: document.getElementById('edit-inv-date').value,
        customer_name: document.getElementById('edit-customer-name').value,
        address: document.getElementById('edit-address').value,
        description: document.getElementById('edit-description').value,
        category: document.getElementById('edit-category').value,
        total_amount: parseFloat(document.getElementById('edit-total-amount').value) || 0,
        payment_method: document.getElementById('edit-payment-method').value,
        status: document.getElementById('edit-status').value || 'Lunas',
        notes: document.getElementById('edit-notes').value || ''
      };

      const editCustomInputs = document.querySelectorAll('#edit-custom-fields-container [data-edit-custom-key]');
      editCustomInputs.forEach(inp => {
        payload[inp.getAttribute('data-edit-custom-key')] = inp.value;
      });

      try {
        const resp = await fetch('/api/update-record', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(payload)
        });
        const res = await resp.json();
        if (res.success) {
          showToast('Data transaksi berhasil diperbarui!');
          closeEditModal();
          loadMonitorRecords(true);
        } else {
          showToast('Gagal update: ' + (res.message || 'Error'));
        }
      } catch (err) {
        showToast('Error update: ' + err.message);
      }
    }

    async function deleteRecordAction(invNum, rowId) {
      if (!confirm(`Yakin ingin menghapus transaksi #${invNum || rowId}?`)) return;
      try {
        let targetDriveUrl = '';
        window._deletedTempIds = window._deletedTempIds || new Set();
        if (rowId) window._deletedTempIds.add(rowId);

        // Tampilkan feedback langsung & hapus optimistik dari UI
        if (Array.isArray(monitorRecordsCache)) {
          const found = monitorRecordsCache.find(r => (rowId && r.id == rowId) || (!rowId && r.invoice_number == invNum));
          if (found && found.drive_url && String(found.drive_url).startsWith('http')) targetDriveUrl = found.drive_url;
          if (rowId) {
            monitorRecordsCache = monitorRecordsCache.filter(r => r.id != rowId);
          } else {
            monitorRecordsCache = monitorRecordsCache.filter(r => r.invoice_number != invNum);
          }
          renderDashboardStats(monitorRecordsCache);
          renderRecentInvoices(monitorRecordsCache);
          renderTopClients(monitorRecordsCache);
          renderTransactionsTable(monitorRecordsCache);
          const sbCount = document.getElementById('sidebar-tx-count');
          if (sbCount) sbCount.textContent = monitorRecordsCache.length;
        }

        // Jika baris ini baru saja di-Auto-Save dan proses simpan ke Sheets/Drive masih berjalan, tunggu sampai selesai agar row_id & drive_url akurat
        if (rowId && window._activeSaves && window._activeSaves[rowId]) {
          const savedInfo = await window._activeSaves[rowId];
          if (savedInfo && savedInfo.row_id) rowId = savedInfo.row_id;
          if (savedInfo && savedInfo.drive_url && String(savedInfo.drive_url).startsWith('http')) targetDriveUrl = savedInfo.drive_url;
        }

        const resp = await fetch('/api/delete-record', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ invoice_number: invNum, row_id: rowId, drive_url: targetDriveUrl })
        });
        const res = await resp.json();
        if (res.success) {
          showToast('Transaksi berhasil dihapus');
          // Refresh background sinkron dari sheets
          setTimeout(() => {
            loadMonitorRecords(true);
          }, 600);
        } else {
          showToast('Gagal: ' + (res.message || 'Gagal menghapus'));
          loadMonitorRecords(true);
        }
      } catch (err) {
        showToast('Gagal menghapus: ' + err.message);
        loadMonitorRecords(true);
      }
    }

    // Clients Manager
    async function loadClients() {
      try {
        const resp = await fetch('/api/clients');
        const clients = await resp.json();
        clientsCache = clients;
        const tbody = document.getElementById('clients-tbody');
        tbody.innerHTML = '';
        for (const [k, v] of Object.entries(clients)) {
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td class="px-4 py-2 font-mono font-bold"><input type="text" value="${k}" class="client-key w-full bg-transparent border-0 font-bold focus:ring-1 focus:ring-brandTeal p-1 rounded"></td>
            <td class="px-4 py-2"><input type="text" value="${v}" class="client-val w-full bg-transparent border-0 font-medium focus:ring-1 focus:ring-brandTeal p-1 rounded"></td>
            <td class="px-4 py-2 text-center"><button onclick="this.closest('tr').remove()" class="text-rose-500 hover:text-rose-700 text-xs">&times;</button></td>
          `;
          tbody.appendChild(tr);
        }
      } catch (e) {
        console.error('Error loading clients', e);
      }
    }

    function addNewClientRow() {
      const tbody = document.getElementById('clients-tbody');
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td class="px-4 py-2 font-mono font-bold"><input type="text" placeholder="MISAL: ABC" class="client-key w-full bg-white border border-slate-200 font-bold focus:ring-1 focus:ring-brandTeal p-1 rounded"></td>
        <td class="px-4 py-2"><input type="text" placeholder="PT Anugerah Berkah Cipta" class="client-val w-full bg-white border border-slate-200 font-medium focus:ring-1 focus:ring-brandTeal p-1 rounded"></td>
        <td class="px-4 py-2 text-center"><button onclick="this.closest('tr').remove()" class="text-rose-500 hover:text-rose-700 text-xs">&times;</button></td>
      `;
      tbody.prepend(tr);
    }

    async function saveClientsDictionary() {
      const rows = document.querySelectorAll('#clients-tbody tr');
      const newClients = {};
      rows.forEach(r => {
        const k = r.querySelector('.client-key').value.trim().toUpperCase();
        const v = r.querySelector('.client-val').value.trim();
        if (k && v) newClients[k] = v;
      });

      const resp = await fetch('/api/clients', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(newClients)
      });
      const res = await resp.json();
      if (res.success) {
        showToast('Kamus klien berhasil disimpan!');
        loadClients();
      }
    }

    // Settings
    function toggleAiKeyInputs() {
      const prov = document.getElementById('cfg-ai-provider').value;
      document.querySelectorAll('.provider-key-wrap').forEach(w => w.classList.add('hidden'));
      const active = document.getElementById(`wrapper-${prov}-key`);
      if (active) active.classList.remove('hidden');
    }

    async function loadSettings() {
      try {
        const resp = await fetch('/api/settings');
        const cfg = await resp.json();

        if (cfg.ai_provider) {
          document.getElementById('cfg-ai-provider').value = cfg.ai_provider;
          document.getElementById('top-ai-provider-badge').textContent = `${cfg.ai_provider} AI`;
        }
        toggleAiKeyInputs();

        const provList = ['gemini', 'openai', 'claude', 'nvidia', 'groq', 'openrouter', 'agnes'];
        provList.forEach(p => {
          const inputEl = document.getElementById(`cfg-${p}-key`);
          if (inputEl && cfg[`${p}_api_key_masked`]) {
            inputEl.placeholder = cfg[`${p}_api_key_masked`];
          }
        });

        document.getElementById('cfg-sheets-url').value = cfg.google_sheets_webhook_url || '';
        document.getElementById('cfg-telegram-enabled').checked = cfg.telegram_enabled || false;
        document.getElementById('cfg-telegram-token').value = cfg.telegram_bot_token || '';
        document.getElementById('cfg-telegram-chatid').value = cfg.telegram_chat_id || '';
      } catch (err) {
        console.error(err);
      }
    }

    async function saveAllSettings() {
      const prov = document.getElementById('cfg-ai-provider').value;
      const payload = {
        ai_provider: prov,
        google_sheets_webhook_url: document.getElementById('cfg-sheets-url').value.trim(),
        telegram_enabled: document.getElementById('cfg-telegram-enabled').checked,
        telegram_bot_token: document.getElementById('cfg-telegram-token').value.trim(),
        telegram_chat_id: document.getElementById('cfg-telegram-chatid').value.trim()
      };

      const provList = ['gemini', 'openai', 'claude', 'nvidia', 'groq', 'openrouter', 'agnes'];
      provList.forEach(p => {
        const inputEl = document.getElementById(`cfg-${p}-key`);
        if (inputEl && inputEl.value.trim()) payload[`${p}_api_key`] = inputEl.value.trim();
      });

      const resp = await fetch('/api/settings', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });
      const res = await resp.json();
      if (res.success) {
        showToast('Pengaturan berhasil disimpan!');
        loadSettings();
      }
    }

    async function testAiConnectionAction() {
      const prov = document.getElementById('cfg-ai-provider').value;
      const keyInput = document.getElementById(`cfg-${prov}-key`);
      const keyVal = keyInput ? keyInput.value.trim() : '';

      showToast(`Menguji koneksi ke ${prov.toUpperCase()}...`);
      try {
        const resp = await fetch('/api/test-ai', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ provider: prov, api_key: keyVal })
        });
        const res = await resp.json();
        showToast(res.message);
      } catch (err) {
        showToast('Error: ' + err.message);
      }
    }

    async function testGoogleSheetsConnection() {
      const url = document.getElementById('cfg-sheets-url').value.trim();
      if (!url) return showToast('Masukkan URL Webhook Google Sheets terlebih dahulu!');

      showToast('Menguji webhook Google Sheets & Drive...');
      try {
        const resp = await fetch('/api/test-sheets', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ google_sheets_webhook_url: url })
        });
        const res = await resp.json();
        if (res.success) {
          showToast('✅ Webhook Sheets & Drive Sukses!');
          loadMonitorRecords(true);
        } else {
          showToast('❌ Gagal: ' + res.message);
        }
      } catch (err) {
        showToast('Error: ' + err.message);
      }
    }

    async function testTelegramNotification() {
      const token = document.getElementById('cfg-telegram-token').value.trim();
      const chatId = document.getElementById('cfg-telegram-chatid').value.trim();
      if (!token || !chatId) return showToast('Isi Bot Token dan Chat ID terlebih dahulu!');

      showToast('Mengirim notifikasi tes ke Telegram...');
      try {
        const resp = await fetch('/api/test-telegram', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ telegram_bot_token: token, telegram_chat_id: chatId })
        });
        const res = await resp.json();
        showToast(res.success ? '✅ Telegram terkirim!' : '❌ Gagal: ' + res.message);
      } catch (err) {
        showToast('Error: ' + err.message);
      }
    }

    function copyAppsScriptCode() {
      const code = document.getElementById('code-snippet').innerText;
      navigator.clipboard.writeText(code).then(() => {
        showToast('Kode Apps Script berhasil disalin!');
      });
    }

    // AI Chat Bubble
    function toggleAiChat() {
      const win = document.getElementById('ai-chat-window');
      win.classList.toggle('hidden');
      if (!win.classList.contains('hidden')) {
        document.getElementById('chat-input').focus();
      }
    }

    function sendQuickChat(text) {
      const inp = document.getElementById('chat-input');
      if (inp) {
        inp.value = text;
        sendChatMessage();
      }
    }

    async function sendChatMessage() {
      const inp = document.getElementById('chat-input');
      const msg = inp.value.trim();
      if (!msg) return;
      inp.value = '';

      const container = document.getElementById('chat-messages');
      const userBubble = document.createElement('div');
      userBubble.className = 'flex items-start justify-end gap-2';
      userBubble.innerHTML = `<div class="bg-brandTeal text-white rounded-2xl rounded-tr-sm p-3 leading-relaxed shadow-sm max-w-[85%]">${msg}</div>`;
      container.appendChild(userBubble);

      const loadingBubble = document.createElement('div');
      loadingBubble.className = 'flex items-start gap-2';
      loadingBubble.id = 'chat-bot-loading';
      loadingBubble.innerHTML = `
        <div class="w-7 h-7 rounded-xl bg-brandTealLight text-brandTeal flex items-center justify-center text-xs shrink-0 font-bold">AI</div>
        <div class="bg-slate-100 rounded-2xl rounded-tl-sm p-3 text-slate-400 italic text-xs leading-relaxed shadow-sm flex items-center gap-1.5">
          <i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin"></i> Asisten sedang menganalisis data...
        </div>
      `;
      container.appendChild(loadingBubble);
      container.scrollTop = container.scrollHeight;
      lucide.createIcons();

      try {
        const resp = await fetch('/api/chat', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ message: msg })
        });
        const res = await resp.json();

        loadingBubble.remove();
        const botBubble = document.createElement('div');
        botBubble.className = 'flex items-start gap-2';
        botBubble.innerHTML = `
          <div class="w-7 h-7 rounded-xl bg-brandTealLight text-brandTeal flex items-center justify-center text-xs shrink-0 font-bold">AI</div>
          <div class="bg-slate-100 rounded-2xl rounded-tl-sm p-3 text-slate-800 leading-relaxed shadow-sm max-w-[85%] whitespace-pre-wrap">${res.reply || 'Tidak ada balasan.'}</div>
        `;
        container.appendChild(botBubble);
        container.scrollTop = container.scrollHeight;
      } catch (err) {
        if (loadingBubble) loadingBubble.remove();
        showToast('Error AI chat: ' + err.message);
      }
    }

    // Initialize
    window.addEventListener('DOMContentLoaded', () => {
      initAutoSaveUI();
      loadTableColumns();
      loadSettings();
      loadClients();
      loadMonitorRecords(true);

      // Sinkronisasi background setiap 8 detik
      setInterval(() => {
        const dash = document.getElementById('tab-view-dashboard');
        if (dash && dash.classList.contains('active')) {
          loadMonitorRecords(false);
        }
      }, 8000);
    });
