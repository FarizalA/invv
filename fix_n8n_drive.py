import json

file_path = r'C:\Users\fariz\20\invoice-income-app\n8n_ai_agent_workflow.json'
with open(file_path, 'r', encoding='utf-8') as f:
    wf = json.load(f)

for node in wf.get('nodes', []):
    if node.get('name') == '5A. Parse JSON Hasil AI':
        node['parameters']['jsCode'] = (
            "const text = $json.candidates[0].content.parts[0].text;\n"
            "let parsed = {};\n"
            "try {\n"
            "  const cleanJson = text.replace(/```json/g, '').replace(/```/g, '').trim();\n"
            "  parsed = JSON.parse(cleanJson);\n"
            "} catch(e) {\n"
            "  parsed = { error: 'Gagal parse JSON Gemini', raw: text };\n"
            "}\n\n"
            "try {\n"
            "  const node3A = $('3A. Unduh File Gambar/PDF').first();\n"
            "  if (node3A && node3A.binary && node3A.binary.data) {\n"
            "    parsed.file_base64 = node3A.binary.data.data;\n"
            "    parsed.file_mime = node3A.binary.data.mimeType || 'image/jpeg';\n"
            "  }\n"
            "} catch(err) {\n"
            "  parsed.binary_err = err.toString();\n"
            "}\n\n"
            "return [{ json: parsed }];"
        )

    if node.get('name') == '6A. Simpan ke Google Sheets & Drive':
        body = node['parameters']['jsonBody']
        body = body.replace(
            '"file_base64": "{{ $binary.data ? $binary.data.data : \'\' }}"',
            '"file_base64": "{{ $json.file_base64 || \'\' }}"'
        )
        body = body.replace(
            '"file_mime": "{{ $binary.data ? $binary.data.mimeType : \'image/jpeg\' }}"',
            '"file_mime": "{{ $json.file_mime || \'image/jpeg\' }}"'
        )
        node['parameters']['jsonBody'] = body

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(wf, f, indent=2, ensure_ascii=False)

print('Updated 5A and 6A successfully!')
