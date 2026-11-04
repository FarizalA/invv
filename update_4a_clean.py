import json

file_path = r'C:\Users\fariz\20\invoice-income-app\n8n_ai_agent_workflow.json'
with open(file_path, 'r', encoding='utf-8') as f:
    wf = json.load(f)

api_key = 'AQ.Ab8RN6K1FbOKhiBfJp_Z9iTOb3VCco7xAqkwQ42At7fzZgbIZg'

for node in wf.get('nodes', []):
    if node.get('name') == '4A. Gemini Ekstraksi Bukti':
        node['parameters']['url'] = f'=https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={api_key}'
        node['parameters']['jsonBody'] = (
            "={\n"
            '  "contents": [\n'
            '    {\n'
            '      "parts": [\n'
            '        {\n'
            '          "inlineData": {\n'
            '            "mimeType": "{{ $binary.data ? $binary.data.mimeType : \'image/jpeg\' }}",\n'
            '            "data": "{{ $binary.data ? $binary.data.data : \'\' }}"\n'
            '          }\n'
            '        },\n'
            '        {\n'
            '          "text": "Anda adalah AI akuntansi ahli ekstraksi dokumen PEMASUKAN (Sales Invoice, Bukti Transfer, Nota Penjualan). Ekstrak data: No. Invoice, Tanggal (YYYY-MM-DD), Nama Klien (jika inisial: FA -> Fariz Abidin, MBP -> PT Maju Bersama Perkasa), Deskripsi, Kategori, Subtotal, Pajak, Diskon, Total Nominal (angka murni), Bank Tujuan, Status (Lunas/DP). Output WAJIB HANYA JSON murni tanpa markdown: {\\"invoice_number\\":\\"...\\",\\"invoice_date\\":\\"...\\",\\"customer_name\\":\\"...\\",\\"description\\":\\"...\\",\\"category\\":\\"...\\",\\"subtotal\\":0,\\"tax\\":0,\\"discount\\":0,\\"total_amount\\":0,\\"payment_method\\":\\"...\\",\\"status\\":\\"Lunas\\"}"\n'
            '        }\n'
            '      ]\n'
            '    }\n'
            '  ],\n'
            '  "generationConfig": {\n'
            '    "response_mime_type": "application/json"\n'
            '  }\n'
            "}"
        )
    if node.get('name') == 'Gemini Chat Model':
        node['parameters']['modelName'] = 'gemini-3.1-flash-lite-preview'

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(wf, f, indent=2, ensure_ascii=False)

print('Updated 4A with gemini-3.1-flash-lite-preview and camelCase inlineData!')
