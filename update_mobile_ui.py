file_path = r'C:\Users\fariz\20\invoice-income-app\templates\index.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update header logo container
content = content.replace(
    'class="flex items-center gap-2.5 sm:gap-3 shrink-0"',
    'class="hidden sm:flex items-center gap-2.5 sm:gap-3 shrink-0"'
)

# 2. Update nav on mobile to take full width and space between
content = content.replace(
    '<nav class="flex space-x-1 sm:space-x-2 overflow-x-auto no-scrollbar py-1">',
    '<nav class="flex space-x-1 sm:space-x-2 overflow-x-auto no-scrollbar py-1 w-full sm:w-auto justify-between sm:justify-end">'
)

# 3. Hide 4 cards on mobile
content = content.replace(
    '<div class="grid grid-cols-2 sm:grid-cols-4 gap-2.5 sm:gap-4">',
    '<div class="hidden md:grid md:grid-cols-4 gap-4">'
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated index.html successfully!')
