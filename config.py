import os
import json
import shutil
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

if os.environ.get("VERCEL"):
    DATA_DIR = Path("/tmp/data")
else:
    DATA_DIR = BASE_DIR / "data"

try:
    DATA_DIR.mkdir(exist_ok=True, parents=True)
except Exception:
    pass

CONFIG_FILE = DATA_DIR / "config.json"
ORIGINAL_CONFIG = BASE_DIR / "data" / "config.json"

if os.environ.get("VERCEL") and not CONFIG_FILE.exists() and ORIGINAL_CONFIG.exists():
    try:
        shutil.copy(ORIGINAL_CONFIG, CONFIG_FILE)
    except Exception:
        pass

# Muat dari .env jika ada
load_dotenv(BASE_DIR / ".env")

DEFAULT_CONFIG = {
    "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
    "gemini_model": "gemini-3-flash-preview",
    "google_sheets_webhook_url": os.getenv("GOOGLE_SHEETS_WEBHOOK_URL", ""),
    "telegram_enabled": False,
    "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
    "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID", ""),
    "whatsapp_enabled": False,
    "whatsapp_provider": "fonnte",  # "fonnte" atau "generic"
    "whatsapp_api_url": "https://api.fonnte.com/send",
    "whatsapp_api_token": os.getenv("WHATSAPP_API_TOKEN", ""),
    "whatsapp_target_phone": os.getenv("WHATSAPP_TARGET_PHONE", ""),
    "default_bank": "BCA",
    "default_category": "Jasa Layanan"
}

def load_config() -> dict:
    config = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                config.update(saved)
        except Exception as e:
            print(f"[Config] Error membaca config.json: {e}")
            
    # Di Vercel / Cloud: prioritaskan Environment Variables jika ada
    env_gemini = os.getenv("GEMINI_API_KEY", "").strip()
    if env_gemini:
        config["gemini_api_key"] = env_gemini
    env_sheets = os.getenv("GOOGLE_SHEETS_WEBHOOK_URL", "").strip()
    if env_sheets:
        config["google_sheets_webhook_url"] = env_sheets
    env_tg_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if env_tg_token:
        config["telegram_bot_token"] = env_tg_token
    env_tg_chat = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if env_tg_chat:
        config["telegram_chat_id"] = env_tg_chat

    return config

def save_config(new_data: dict) -> dict:
    current = load_config()
    current.update(new_data)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2, ensure_ascii=False)
    return current
