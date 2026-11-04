# Update templates/index.html
file_path = r'C:\Users\fariz\20\invoice-income-app\templates\index.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove logo and title container completely from header
import re

old_header_block = re.search(r'<header.*?</header>', content, re.DOTALL)
if old_header_block:
    new_header = '''<header class="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-sm">
    <div class="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between sm:justify-start h-16 gap-2 sm:gap-4">
        <!-- Nav Tabs -->
        <nav class="flex space-x-1 sm:space-x-2 overflow-x-auto no-scrollbar py-1 w-full sm:w-auto justify-between sm:justify-start">
          <button onclick="switchTab('tab-main')" id="nav-main" class="nav-btn px-3 py-2 rounded-lg text-xs sm:text-sm font-semibold transition-all bg-blue-50 text-blue-700 flex items-center gap-1.5 shrink-0">
            <i data-lucide="layout-dashboard" class="w-4 h-4"></i>
            <span>Dashboard</span>
          </button>
          <button onclick="switchTab('tab-clients')" id="nav-clients" class="nav-btn px-3 py-2 rounded-lg text-xs sm:text-sm font-semibold transition-all text-slate-600 hover:text-slate-900 hover:bg-slate-100 flex items-center gap-1.5 shrink-0">
            <i data-lucide="users" class="w-4 h-4"></i>
            <span>Klien</span>
          </button>
          <button onclick="switchTab('tab-settings')" id="nav-settings" class="nav-btn px-3 py-2 rounded-lg text-xs sm:text-sm font-semibold transition-all text-slate-600 hover:text-slate-900 hover:bg-slate-100 flex items-center gap-1.5 shrink-0">
            <i data-lucide="settings" class="w-4 h-4"></i>
            <span>Pengaturan</span>
          </button>
          <button onclick="switchTab('tab-guide')" id="nav-guide" class="nav-btn px-3 py-2 rounded-lg text-xs sm:text-sm font-semibold transition-all text-slate-600 hover:text-slate-900 hover:bg-slate-100 flex items-center gap-1.5 shrink-0">
            <i data-lucide="book-open" class="w-4 h-4"></i>
            <span>Panduan</span>
          </button>
        </nav>
      </div>
    </div>
  </header>'''
    content = content[:old_header_block.start()] + new_header + content[old_header_block.end():]

# 2. Add id to 4 stat cards container
content = re.sub(
    r'<!-- Summary Stats Cards.*?-->\s*<div[^>]*>',
    '<!-- Summary Stats Cards (Sembunyikan di Mobile) -->\n        <div id="summary-stats-cards" class="hidden md:grid md:grid-cols-4 gap-4">',
    content
)

# 3. Add explicit CSS in <style> to guarantee hiding on mobile
mobile_css = '''
    /* Sembunyikan 4 cards di mobile */
    @media (max-width: 768px) {
      #summary-stats-cards {
        display: none !important;
      }
    }
'''
if '/* Sembunyikan 4 cards di mobile */' not in content:
    content = content.replace('</style>', mobile_css + '\n  </style>')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated index.html completely!')
