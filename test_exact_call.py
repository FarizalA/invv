import urllib.request, ssl, base64, json
ctx = ssl._create_unverified_context()
api_key = 'AQ.Ab8RN6K1FbOKhiBfJp_Z9iTOb3VCco7xAqkwQ42At7fzZgbIZg'
token = '8596322208:AAFCPPOArpjrOyXyRwpm4Qw-DqcGvRgcrbY'
file_url = f'https://api.telegram.org/file/bot{token}/photos/file_3.jpg'
req = urllib.request.Request(file_url, headers={'User-Agent': 'Mozilla/5.0'})
img_bytes = urllib.request.urlopen(req, context=ctx).read()
b64_clean = base64.b64encode(img_bytes).decode('utf-8')

prompt = (
    "Anda adalah AI akuntansi ahli ekstraksi dokumen PEMASUKAN. "
    "Ekstrak data: invoice_number, invoice_date (YYYY-MM-DD), customer_name, description, category, "
    "subtotal, tax, discount, total_amount, payment_method, status (Lunas). "
    "Output JSON murni."
)

payload = {
    'contents': [{
        'parts': [
            {'inlineData': {'mimeType': 'image/jpeg', 'data': b64_clean}},
            {'text': prompt}
        ]
    }],
    'generationConfig': {
        'response_mime_type': 'application/json'
    }
}
url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={api_key}'
req_g = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
res = urllib.request.urlopen(req_g, context=ctx)
print('SUCCESS! Response:', res.read().decode('utf-8'))
