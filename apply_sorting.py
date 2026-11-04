import json

# 1. Update app.py sorting
file_app = r'C:\Users\fariz\20\invoice-income-app\app.py'
with open(file_app, 'r', encoding='utf-8') as f:
    code = f.read()

# Make sure final_rows is sorted before caching
sort_logic = '''            if final_rows:
                # Urutkan dari transaksi terbaru (tanggal terbaru & ID terbesar di atas)
                def get_sort_key(item):
                    d = str(item.get("invoice_date") or "1970-01-01")
                    i = int(item.get("id") or 0)
                    return (d, i)
                final_rows.sort(key=get_sort_key, reverse=True)
'''

code = code.replace(
    '            if final_rows:\n                # Perbarui file cache lokal dan memory cache',
    sort_logic + '                # Perbarui file cache lokal dan memory cache'
)

with open(file_app, 'w', encoding='utf-8') as f:
    f.write(code)

# 2. Update templates/index.html sorting
file_html = r'C:\Users\fariz\20\invoice-income-app\templates\index.html'
with open(file_html, 'r', encoding='utf-8') as f:
    html = f.read()

old_load = '''          if (res.success) {
            monitorRecordsCache = res.rows || [];
            if (res.spreadsheet_url) {'''

new_load = '''          if (res.success) {
            monitorRecordsCache = res.rows || [];
            // Pastikan urutkan dari transaksi paling baru ke lama
            monitorRecordsCache.sort((a, b) => {
              const dateA = a.invoice_date || '1970-01-01';
              const dateB = b.invoice_date || '1970-01-01';
              if (dateB !== dateA) return dateB.localeCompare(dateA);
              return (Number(b.id) || 0) - (Number(a.id) || 0);
            });
            if (res.spreadsheet_url) {'''

html = html.replace(old_load, new_load)

with open(file_html, 'w', encoding='utf-8') as f:
    f.write(html)

print('Updated sorting in app.py and templates/index.html successfully!')
