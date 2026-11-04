import json

file_path = r'C:\Users\fariz\20\invoice-income-app\n8n_ai_agent_workflow.json'

api_key = 'AQ.Ab8RN6K1FbOKhiBfJp_Z9iTOb3VCco7xAqkwQ42At7fzZgbIZg'
script_url = 'https://script.google.com/macros/s/AKfycbxtbP26drGs9uMBDcB8RH9Jb1DrScw72bQPD28ySi6k1dvQRExAcUFhPyFOzB0z4bLJgQ/exec'

nodes = [
  {
    "parameters": {
      "updates": ["message"]
    },
    "id": "10000000-0000-0000-0000-000000000001",
    "name": "1. Telegram Trigger",
    "type": "n8n-nodes-base.telegramTrigger",
    "typeVersion": 1.1,
    "position": [160, 380]
  },
  {
    "parameters": {
      "conditions": {
        "options": {
          "caseSensitive": True,
          "leftValue": "",
          "typeValidation": "strict",
          "version": 2
        },
        "conditions": [
          {
            "id": "c1",
            "leftValue": "={{ $json.message.photo || $json.message.document ? 'file' : 'text' }}",
            "rightValue": "file",
            "operator": {
              "type": "string",
              "operation": "equals"
            }
          }
        ],
        "combinator": "and"
      }
    },
    "id": "10000000-0000-0000-0000-000000000002",
    "name": "2. Filter: File atau Pertanyaan Teks?",
    "type": "n8n-nodes-base.if",
    "typeVersion": 2.2,
    "position": [380, 380]
  },
  {
    "parameters": {
      "resource": "file",
      "operation": "get",
      "fileId": "={{ $json.message.photo ? $json.message.photo[$json.message.photo.length - 1].file_id : $json.message.document.file_id }}",
      "download": True
    },
    "id": "10000000-0000-0000-0000-000000000003",
    "name": "3A. Unduh File Gambar/PDF",
    "type": "n8n-nodes-base.telegram",
    "typeVersion": 1.2,
    "position": [600, 220]
  },
  {
    "parameters": {
      "jsCode": """// Ambil binary dari n8n Cloud filesystem secara aman
const binaryBuffer = await this.helpers.getBinaryDataBuffer(0, 'data');
const base64Data = binaryBuffer.toString('base64');
const mimeType = $binary.data ? $binary.data.mimeType : 'image/jpeg';

return [{
  json: {
    image_base64: base64Data,
    image_mime: mimeType,
    chat_id: $('1. Telegram Trigger').first().json.message.chat.id
  }
}];"""
    },
    "id": "10000000-0000-0000-0000-000000000035",
    "name": "3B. Siapkan Gambar Base64",
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [800, 220]
  },
  {
    "parameters": {
      "method": "POST",
      "url": f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={api_key}",
      "sendBody": True,
      "specifyBody": "json",
      "jsonBody": """={
  "contents": [
    {
      "parts": [
        {
          "inlineData": {
            "mimeType": "{{ $json.image_mime }}",
            "data": "{{ $json.image_base64 }}"
          }
        },
        {
          "text": "Anda adalah AI akuntansi ahli ekstraksi dokumen PEMASUKAN (Sales Invoice, Bukti Transfer, Nota Penjualan). Ekstrak data: No. Invoice, Tanggal (YYYY-MM-DD), Nama Klien (jika inisial: FA -> Fariz Abidin, MBP -> PT Maju Bersama Perkasa), Deskripsi, Kategori, Subtotal, Pajak, Diskon, Total Nominal (angka murni), Bank Tujuan, Status (Lunas/DP). Output WAJIB HANYA JSON murni tanpa markdown: {\\"invoice_number\\\":\\\"...\\\",\\\"invoice_date\\\":\\\"...\\\",\\\"customer_name\\\":\\\"...\\\",\\\"description\\\":\\\"...\\\",\\\"category\\\":\\\"...\\\",\\\"subtotal\\\":0,\\\"tax\\\":0,\\\"discount\\\":0,\\\"total_amount\\\":0,\\\"payment_method\\\":\\\"...\\\",\\\"status\\\":\\\"Lunas\\\"}"
        }
      ]
    }
  ],
  "generationConfig": {
    "response_mime_type": "application/json"
  }
}"""
    },
    "id": "10000000-0000-0000-0000-000000000004",
    "name": "4A. Gemini Ekstraksi Bukti",
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "position": [1020, 220]
  },
  {
    "parameters": {
      "jsCode": """const text = $json.candidates[0].content.parts[0].text;
let parsed = {};
try {
  const cleanJson = text.replace(/```json/g, '').replace(/```/g, '').trim();
  parsed = JSON.parse(cleanJson);
} catch(e) {
  parsed = { error: 'Gagal parse JSON Gemini', raw: text };
}

// Bawa base64 gambar dari node 3B untuk dikirim ke Google Drive
try {
  const imgNode = $('3B. Siapkan Gambar Base64').first();
  if (imgNode && imgNode.json && imgNode.json.image_base64) {
    parsed.file_base64 = imgNode.json.image_base64;
    parsed.file_mime = imgNode.json.image_mime || 'image/jpeg';
  }
} catch(err) {
  parsed.binary_err = err.toString();
}

return [{ json: parsed }];"""
    },
    "id": "10000000-0000-0000-0000-000000000005",
    "name": "5A. Parse JSON Hasil AI",
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [1240, 220]
  },
  {
    "parameters": {
      "method": "POST",
      "url": script_url,
      "sendBody": True,
      "specifyBody": "json",
      "jsonBody": """={
  "invoice_number": "{{ $json.invoice_number || '-' }}",
  "invoice_date": "{{ $json.invoice_date || '-' }}",
  "customer_name": "{{ $json.customer_name || 'Pelanggan Umum' }}",
  "description": "{{ $json.description || '-' }}",
  "category": "{{ $json.category || 'Pemasukan' }}",
  "subtotal": {{ $json.subtotal || 0 }},
  "tax": {{ $json.tax || 0 }},
  "discount": {{ $json.discount || 0 }},
  "total_amount": {{ $json.total_amount || 0 }},
  "payment_method": "{{ $json.payment_method || '-' }}",
  "status": "{{ $json.status || 'Lunas' }}",
  "notes": "Dicatat otomatis via Telegram Bot",
  "file_base64": "{{ $json.file_base64 || '' }}",
  "file_name": "Bukti_{{ $json.invoice_number || 'transfer' }}.jpg",
  "file_mime": "{{ $json.file_mime || 'image/jpeg' }}"
}"""
    },
    "id": "10000000-0000-0000-0000-000000000006",
    "name": "6A. Simpan ke Google Sheets & Drive",
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "position": [1460, 220]
  },
  {
    "parameters": {
      "chatId": "={{ $('1. Telegram Trigger').first().json.message.chat.id }}",
      "text": "=✅ *PEMASUKAN BARU BERHASIL DICATAT!*\n━━━━━━━━━━━━━━━━━━━━\n👤 *Klien:* {{ $('5A. Parse JSON Hasil AI').first().json.customer_name }}\n🧾 *No. Ref/Inv:* `{{ $('5A. Parse JSON Hasil AI').first().json.invoice_number }}`\n💰 *Total:* Rp {{ Number($('5A. Parse JSON Hasil AI').first().json.total_amount || 0).toLocaleString('id-ID') }}\n🏦 *Bank / Metode:* {{ $('5A. Parse JSON Hasil AI').first().json.payment_method }}\n📌 *Status:* {{ $('5A. Parse JSON Hasil AI').first().json.status }}\n\n📂 *Bukti Drive:* {{ $json.drive_url }}\n\n💡 _Ketik pertanyaan seperti \"Berapa total pemasukan bulan ini?\" untuk ngobrol dengan AI Agen._",
      "additionalFields": {
        "parse_mode": "Markdown"
      }
    },
    "id": "10000000-0000-0000-0000-000000000007",
    "name": "7A. Notifikasi Teks ke Telegram",
    "type": "n8n-nodes-base.telegram",
    "typeVersion": 1.2,
    "position": [1680, 220]
  },
  {
    "parameters": {
      "promptType": "define",
      "text": "={{ $json.message.text }}",
      "options": {
        "systemMessage": "=Anda adalah AI Agen Keuangan & Pembukuan pribadi yang ramah, cerdas, dan teliti.\nTugas utama Anda adalah:\n1. Membantu pengguna melihat, mengecek, menghitung, dan menganalisis data keuangan pemasukan yang ada di Google Sheets.\n2. SELALU gunakan Tool 'Ambil_Data_Google_Sheets' untuk mendapatkan data transaksi riil terkini saat pengguna bertanya tentang pemasukan, klien, saldo, invoice, dsb.\n3. Berikan jawaban dalam Bahasa Indonesia yang sopan, rapi (gunakan format Rupiah seperti Rp 150.000, poin-poin, dan emotikon yang sesuai).\n4. Jika ditanya tentang total, hitung akumulasi nominal dengan tepat berdasarkan data riil dari Google Sheets."
      }
    },
    "id": "20000000-0000-0000-0000-000000000001",
    "name": "3B. AI Agent Keuangan",
    "type": "@n8n/n8n-nodes-langchain.agent",
    "typeVersion": 1.7,
    "position": [680, 540]
  },
  {
    "parameters": {
      "modelName": "gemini-3.1-flash-lite-preview",
      "options": {
        "temperature": 0.2
      }
    },
    "id": "20000000-0000-0000-0000-000000000002",
    "name": "Gemini Chat Model",
    "type": "@n8n/n8n-nodes-langchain.lmChatGoogleGemini",
    "typeVersion": 1,
    "position": [600, 740]
  },
  {
    "parameters": {
      "name": "Ambil_Data_Google_Sheets",
      "description": "Gunakan tool ini untuk mengambil seluruh riwayat transaksi keuangan pemasukan, daftar invoice, nama klien, tanggal, nominal uang, status pembayaran, dan bank langsung dari Google Sheets.",
      "url": script_url
    },
    "id": "20000000-0000-0000-0000-000000000003",
    "name": "Tool: Data Google Sheets",
    "type": "@n8n/n8n-nodes-langchain.toolHttpRequest",
    "typeVersion": 1.1,
    "position": [780, 740]
  },
  {
    "parameters": {
      "chatId": "={{ $('1. Telegram Trigger').first().json.message.chat.id }}",
      "text": "={{ $json.output }}",
      "additionalFields": {}
    },
    "id": "20000000-0000-0000-0000-000000000005",
    "name": "4B. Kirim Balasan AI ke Telegram",
    "type": "n8n-nodes-base.telegram",
    "typeVersion": 1.2,
    "position": [1020, 540]
  }
]

connections = {
  "1. Telegram Trigger": {
    "main": [
      [{"node": "2. Filter: File atau Pertanyaan Teks?", "type": "main", "index": 0}]
    ]
  },
  "2. Filter: File atau Pertanyaan Teks?": {
    "main": [
      [{"node": "3A. Unduh File Gambar/PDF", "type": "main", "index": 0}],
      [{"node": "3B. AI Agent Keuangan", "type": "main", "index": 0}]
    ]
  },
  "3A. Unduh File Gambar/PDF": {
    "main": [
      [{"node": "3B. Siapkan Gambar Base64", "type": "main", "index": 0}]
    ]
  },
  "3B. Siapkan Gambar Base64": {
    "main": [
      [{"node": "4A. Gemini Ekstraksi Bukti", "type": "main", "index": 0}]
    ]
  },
  "4A. Gemini Ekstraksi Bukti": {
    "main": [
      [{"node": "5A. Parse JSON Hasil AI", "type": "main", "index": 0}]
    ]
  },
  "5A. Parse JSON Hasil AI": {
    "main": [
      [{"node": "6A. Simpan ke Google Sheets & Drive", "type": "main", "index": 0}]
    ]
  },
  "6A. Simpan ke Google Sheets & Drive": {
    "main": [
      [{"node": "7A. Notifikasi Teks ke Telegram", "type": "main", "index": 0}]
    ]
  },
  "3B. AI Agent Keuangan": {
    "main": [
      [{"node": "4B. Kirim Balasan AI ke Telegram", "type": "main", "index": 0}]
    ]
  },
  "Gemini Chat Model": {
    "ai_languageModel": [
      [{"node": "3B. AI Agent Keuangan", "type": "ai_languageModel", "index": 0}]
    ]
  },
  "Tool: Data Google Sheets": {
    "ai_tool": [
      [{"node": "3B. AI Agent Keuangan", "type": "ai_tool", "index": 0}]
    ]
  }
}

full_wf = {
  "name": "Invoice Income to Drive & Sheets + AI Agent",
  "nodes": nodes,
  "connections": connections,
  "active": True,
  "settings": {
    "executionOrder": "v1"
  }
}

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(full_wf, f, indent=2, ensure_ascii=False)

print('Saved perfect n8n cloud workflow!')
