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
    - Jika nama berupa inisial atau cocok dengan kamus alias, otomatis kembalikan nama lengkap.
    - Menghasilkan status apakah nama di-enrich otomatis atau tidak.
    """
    clients = load_clients()
    
    # 1. Bersihkan input
    name_clean = (extracted_name or "").strip()
    initial_clean = (extracted_initials or "").strip()
    
    candidates = []
    if initial_clean:
        candidates.append(initial_clean)
    if name_clean:
        candidates.append(name_clean)
        # Jika nama pendek (<= 5 karakter, misal "PT XYZ", "FA", "Bpk A")
        if len(name_clean) <= 6:
            candidates.append(name_clean.replace(".", "").replace(" ", "").upper())
    
    # 2. Cek kecocokan di kamus alias
    matched_alias = None
    resolved_full_name = None
    
    for cand in candidates:
        cand_upper = cand.upper()
        # Direct key match
        for key, full in clients.items():
            if key.upper() == cand_upper:
                matched_alias = key
                resolved_full_name = full
                break
        if resolved_full_name:
            break
            
    if resolved_full_name:
        return {
            "customer_name": resolved_full_name,
            "raw_name": name_clean or initial_clean,
            "is_resolved_from_alias": True,
            "matched_alias": matched_alias,
            "note": f"Otomatis dilengkapi dari inisial '{matched_alias}'"
        }
        
    # 3. Jika nama kosong sama sekali
    if not name_clean and not initial_clean:
        return {
            "customer_name": "Pelanggan Umum (Tanpa Nama)",
            "raw_name": "",
            "is_resolved_from_alias": False,
            "matched_alias": None,
            "note": "Nama tidak ditemukan di invoice, menggunakan default"
        }
        
    # 4. Jika nama terdeteksi hanya inisial / sangat singkat tapi belum terdaftar di kamus
    is_short = len(name_clean) <= 4 or name_clean.isupper()
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
    Otomatis menyimpan alias baru jika user mengoreksi/mengisi nama lengkap dari sebuah inisial
    """
    if not raw_or_initial or not full_name:
        return
    raw = raw_or_initial.strip().upper()
    full = full_name.strip()
    
    # Hanya simpan jika raw adalah inisial/singkatan yang berbeda dengan full_name
    if len(raw) <= 10 and raw.upper() != full.upper():
        clients = load_clients()
        clients[raw] = full
        save_clients(clients)
        print(f"[ClientManager] Auto-learned alias: {raw} -> {full}")
