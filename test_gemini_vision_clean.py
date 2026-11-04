import urllib.request, ssl, base64, json

ctx = ssl._create_unverified_context()
token = '8596322208:AAFCPPOArpjrOyXyRwpm4Qw-DqcGvRgcrbY'
api_key = 'AQ.Ab8RN6K1FbOKhiBfJp_Z9iTOb3VCco7xAqkwQ42At7fzZgbIZg'

file_url = f'https://api.telegram.org/file/bot{token}/photos/file_3.jpg'
req = urllib.request.Request(file_url, headers={'User-Agent': 'Mozilla/5.0'})
img_bytes = urllib.request.urlopen(req, context=ctx).read()

# Test what happens if we strip newlines:
b64_clean = base64.b64encode(img_bytes).decode('utf-8').replace('\n', '').replace('\r', '')

payload = {
    'contents': [{
        'parts': [
            {'inline_data': {'mime_type': 'image/jpeg', 'data': b64_clean}},
            {'text': 'Ekstrak data: No. Invoice, Tanggal, Nama Klien, Total Nominal, Bank Tujuan, Status. Output JSON murni.'}
        ]
    }],
    'generationConfig': {
        'response_mime_type': 'application/json'
    }
}

gemini_url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}'
req_g = urllib.request.Request(gemini_url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
try:
    res = urllib.request.urlopen(req_g, context=ctx)
    print('SUCCESS! Response:', res.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print('Error:', e.code, e.read().decode('utf-8'))
