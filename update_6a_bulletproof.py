import json

file_path = r'C:\Users\fariz\20\invoice-income-app\n8n_ai_agent_workflow.json'
with open(file_path, 'r', encoding='utf-8') as f:
    wf = json.load(f)

for node in wf.get('nodes', []):
    if node.get('name') == '6A. Simpan ke Google Sheets & Drive':
        body = {
            "invoice_number": "={{ $json.invoice_number || '-' }}",
            "invoice_date": "={{ $json.invoice_date || '-' }}",
            "customer_name": "={{ $json.customer_name || 'Pelanggan Umum' }}",
            "description": "={{ $json.description || '-' }}",
            "category": "={{ $json.category || 'Pemasukan' }}",
            "subtotal": "={{ $json.subtotal || 0 }}",
            "tax": "={{ $json.tax || 0 }}",
            "discount": "={{ $json.discount || 0 }}",
            "total_amount": "={{ $json.total_amount || 0 }}",
            "payment_method": "={{ $json.payment_method || '-' }}",
            "status": "={{ $json.status || 'Lunas' }}",
            "notes": "Dicatat otomatis via Telegram Bot",
            "file_base64": "={{ $json.file_base64 ? $json.file_base64 : ($('3A. Unduh File Gambar/PDF').first().binary && $('3A. Unduh File Gambar/PDF').first().binary.data ? $('3A. Unduh File Gambar/PDF').first().binary.data.data : '') }}",
            "file_name": "Bukti_{{ $json.invoice_number || 'transfer' }}.jpg",
            "file_mime": "={{ $json.file_mime ? $json.file_mime : ($('3A. Unduh File Gambar/PDF').first().binary && $('3A. Unduh File Gambar/PDF').first().binary.data ? $('3A. Unduh File Gambar/PDF').first().binary.data.mimeType : 'image/jpeg') }}"
        }
        # In n8n jsonBody is a string representing the JSON object
        node['parameters']['jsonBody'] = "={\n" + ",\n".join([f'  "{k}": "{v}"' if not k in ['subtotal', 'tax', 'discount', 'total_amount'] else f'  "{k}": {v}' for k, v in body.items()]) + "\n}"

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(wf, f, indent=2, ensure_ascii=False)

print('Updated 6A with bulletproof fallback!')
