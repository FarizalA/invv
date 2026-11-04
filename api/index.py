import sys
import os

# Menambahkan root project ke sys.path agar semua modul (app, config, dll) dapat diimpor oleh Vercel runtime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
