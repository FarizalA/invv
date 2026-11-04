import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if os.environ.get("VERCEL"):
    DB_FILE = Path("/tmp/data/telegram_users.json")
else:
    DB_FILE = BASE_DIR / "data" / "telegram_users.json"

try:
    DB_FILE.parent.mkdir(exist_ok=True, parents=True)
except Exception:
    pass

def load_user_db() -> dict:
    if DB_FILE.exists():
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_user_db(data: dict):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[UserStore] Gagal menyimpan data pengguna: {e}")

def get_user_config(chat_id: str | int) -> dict:
    db = load_user_db()
    return db.get(str(chat_id), {
        "provider": "gemini",
        "api_key": "",
        "sheets_webhook": "",
        "state": "idle"
    })

def set_user_config(chat_id: str | int, updates: dict) -> dict:
    db = load_user_db()
    cid = str(chat_id)
    current = db.get(cid, {
        "provider": "gemini",
        "api_key": "",
        "sheets_webhook": "",
        "state": "idle"
    })
    current.update(updates)
    db[cid] = current
    save_user_db(db)
    return current
