import json

file_path = r'C:\Users\fariz\20\invoice-income-app\n8n_ai_agent_workflow.json'
with open(file_path, 'r', encoding='utf-8') as f:
    wf = json.load(f)

for node in wf.get('nodes', []):
    if node.get('name') == '6A. Simpan ke Google Sheets & Drive':
        node['parameters']['jsonBody'] = (
            "={\n"
            '  "invoice_number": "{{ $json.invoice_number || \'-\' }}",\n'
            '  "invoice_date": "{{ $json.invoice_date || \'-\' }}",\n'
            '  "customer_name": "{{ $json.customer_name || \'Pelanggan Umum\' }}",\n'
            '  "description": "{{ $json.description || \'-\' }}",\n'
            '  "category": "{{ $json.category || \'Pemasukan\' }}",\n'
            '  "subtotal": {{ $json.subtotal || 0 }},\n'
            '  "tax": {{ $json.tax || 0 }},\n'
            '  "discount": {{ $json.discount || 0 }},\n'
            '  "total_amount": {{ $json.total_amount || 0 }},\n'
            '  "payment_method": "{{ $json.payment_method || \'-\' }}",\n'
            '  "status": "{{ $json.status || \'Lunas\' }}",\n'
            '  "notes": "Dicatat otomatis via Telegram Bot",\n'
            '  "file_base64": "{{ $json.file_base64 ? $json.file_base64 : ($(\'3A. Unduh File Gambar/PDF\').first().binary && $(\'3A. Unduh File Gambar/PDF\').first().binary.data ? $(\'3A. Unduh File Gambar/PDF\').first().binary.data.data : \'\') }}",\n'
            '  "file_name": "Bukti_{{ $json.invoice_number || \'transfer\' }}.jpg",\n'
            '  "file_mime": "{{ $json.file_mime ? $json.file_mime : ($(\'3A. Unduh File Gambar/PDF\').first().binary && $(\'3A. Unduh File Gambar/PDF\').first().binary.data ? $(\'3A. Unduh File Gambar/PDF\').first().binary.data.mimeType : \'image/jpeg\') }}"\n'
            "}"
        )

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(wf, f, indent=2, ensure_ascii=False)

print('Cleaned jsonBody in 6A!')
