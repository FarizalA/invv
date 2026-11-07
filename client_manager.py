import os
import json
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

if os.environ.get("VERCEL"):
    DATA_DIR = Path("/tmp/data")
else:
    DATA_DIR = BASE_DIR / "data"

try:
    DATA_DIR.mkdir(exist_ok=True, parents=True)
except Exception:
    pass

CLIENTS_FILE = DATA_DIR / "clients.json"
ORIGINAL_CLIENTS = BASE_DIR / "data" / "clients.json"

if os.environ.get("VERCEL") and not CLIENTS_FILE.exists() and ORIGINAL_CLIENTS.exists():
    try:
        shutil.copy(ORIGINAL_CLIENTS, CLIENTS_FILE)
    except Exception:
        pass

DEFAULT_CLIENTS = {
    "FA": "Fariz Abidin",
    "MBP": "PT Maju Bersama Perkasa",
    "GTS": "PT Global Teknologi Solusi",
    "BDI": "Budi Santoso",
    "TKO": "Pelanggan Tunai Toko"
}

def load_clients() -> dict:
    if not CLIENTS_FILE.exists():
        save_clients(DEFAULT_CLIENTS)
        return DEFAULT_CLIENTS.copy()
    try:
        with open(CLIENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ClientManager] Error loading clients: {e}")
        return DEFAULT_CLIENTS.copy()

def save_clients(clients: dict):
    with open(CLIENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(clients, f, indent=2, ensure_ascii=False)

def resolve_client(extracted_name: str, extracted_initials: str = "") -> dict:
    """
    Menganalisis nama yang diekstrak AI:
    - Jika nama berupa singkatan/kode klien yang terdaftar di kamus alias, otomatis lengkapi ke nama lengkap.
    - PRIORITAS UTAMA: Selalu gunakan nama lengkap asli hasil ekstraksi jika nama tersebut valid (>= 3 karakter).
    - JANGAN PERNAH menimpa nama asli (seperti "DENI") hanya karena inisial 1 huruf (seperti "D") cocok dengan nama lain.
    """
    clients = load_clients()
    
    # 1. Bersihkan input
    name_clean = (extracted_name or "").strip()
    initial_clean = (extracted_initials or "").strip()
    
    # 2. Cek apakah name_clean cocok langsung dengan kamus alias (misal struk/input menulis "FA" atau "MBP")
    matched_alias = None
    resolved_full_name = None
    
    if name_clean:
        name_upper = name_clean.upper()
        # Direct key match dari name_clean
        for key, full in clients.items():
            if key.upper() == name_upper:
                matched_alias = key
                resolved_full_name = full
                break
        
        # Cek jika name_clean sangat pendek (2-6 karakter) tanpa spasi/titik (misal "P.T. XYZ" atau "FA.")
        if not resolved_full_name and 2 <= len(name_clean) <= 6:
            simplified = name_clean.replace(".", "").replace(" ", "").upper()
            for key, full in clients.items():
                if key.upper() == simplified:
                    matched_alias = key
                    resolved_full_name = full
                    break

    # 3. Jika name_clean TIDAK cocok dengan kamus alias, periksa apakah name_clean sudah berupa nama lengkap asli
    # Nama asli valid: panjang >= 3 karakter dan bukan placeholder umum
    is_valid_full_name = len(name_clean) >= 3 and name_clean.lower() not in ["-", "--", "null", "none", "pelanggan umum", "tanpa nama"]
    
    # Jika name_clean sudah nama asli yang valid dan tidak cocok dengan alias manapun,
    # PERTAHANKAN nama asli tersebut! Jangan pernah mencari initial_clean yang bisa menimpa nama asli.
    if is_valid_full_name and not resolved_full_name:
        return {
            "customer_name": name_clean,
            "raw_name": name_clean,
            "is_resolved_from_alias": False,
            "matched_alias": None,
            "is_potential_initial": False,
            "note": ""
        }
        
    # 4. Jika name_clean kosong atau sangat pendek (<= 2 huruf), baru coba cocokkan initial_clean (minimal 2 huruf)
    if not resolved_full_name and initial_clean and len(initial_clean) >= 2:
        init_upper = initial_clean.upper()
        for key, full in clients.items():
            if key.upper() == init_upper:
                matched_alias = key
                resolved_full_name = full
                break

    if resolved_full_name:
        return {
            "customer_name": resolved_full_name,
            "raw_name": name_clean or initial_clean,
            "is_resolved_from_alias": True,
            "matched_alias": matched_alias,
            "note": f"Otomatis dilengkapi dari inisial '{matched_alias}'"
        }
        
    # 5. Jika nama kosong sama sekali
    if not name_clean and not initial_clean:
        return {
            "customer_name": "Pelanggan Umum",
            "raw_name": "",
            "is_resolved_from_alias": False,
            "matched_alias": None,
            "note": "Nama tidak ditemukan di invoice, menggunakan default"
        }
        
    # 6. Jika nama terdeteksi hanya inisial / sangat singkat (2-4 huruf tanpa huruf vokal)
    # Catatan: JANGAN anggap semua huruf kapital sebagai inisial (karena struk bank selalu ALL CAPS, misal DENI)
    is_short = 2 <= len(name_clean) <= 4 and not any(v in name_clean.lower() for v in ['a', 'i', 'u', 'e', 'o'])
    return {
        "customer_name": name_clean,
        "raw_name": name_clean,
        "is_resolved_from_alias": False,
        "matched_alias": None,
        "is_potential_initial": is_short,
        "note": "Inisial baru (akan otomatis disimpan jika Anda mengetik nama lengkap)" if is_short else ""
    }

def record_alias_learning(raw_or_initial: str, full_name: str):
    """
    Otomatis menyimpan alias baru jika user mengoreksi/mengisi nama lengkap dari sebuah inisial.
    SYARAT KETAT:
    - Panjang alias minimal 2 karakter dan maksimal 6 karakter (dilarang keras 1 huruf seperti 'D' atau 'S').
    - Alias tidak boleh sama dengan nama lengkap.
    - Dilarang kata umum perbankan atau istilah transaksi (BCA, DANA, OVO, QRIS, BANK, LUNAS, TRANSFER).
    """
    if not raw_or_initial or not full_name:
        return
    raw = raw_or_initial.strip().upper().replace(".", "").replace(" ", "")
    full = full_name.strip()
    
    # Dilarang inisial 1 huruf (misal 'D', 'S') atau terlalu panjang (> 6 huruf)
    if len(raw) < 2 or len(raw) > 6:
        return
        
    # Dilarang jika singkatan sama persis dengan nama lengkap
    if raw == full.upper().replace(" ", ""):
        return
        
    # Dilarang istilah bank umum atau kata umum
    IGNORED_ALIASES = {"BCA", "BRI", "BNI", "DANA", "OVO", "GOPAY", "QRIS", "BANK", "CASH", "LUNAS", "DP", "TRANSFER", "PEMASUKAN"}
    if raw in IGNORED_ALIASES:
        return
        
    # Hanya simpan jika nama lengkap lebih panjang dari aliasnya
    if len(full) <= len(raw):
        return

    clients = load_clients()
    # Jika sudah ada dan isinya sama, tidak perlu tulis ulang
    if clients.get(raw) == full:
        return
        
    clients[raw] = full
    save_clients(clients)
    print(f"[ClientManager] Auto-learned alias: {raw} -> {full}")
