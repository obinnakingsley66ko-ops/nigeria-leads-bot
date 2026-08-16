"""Central configuration loaded from environment variables.

Nothing here is hard-coded except safe defaults; secrets come from the
environment so the repository stays clean and Render/Railway can inject them.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
DB_PATH = Path(os.getenv("DB_PATH", str(DATA_DIR / "leads.db")))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "0") or "0")

# Webhook mode (set WEBHOOK_URL to enable; otherwise long-polling is used).
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook").strip() or "/webhook"
PORT = int(os.getenv("PORT", "8000") or "8000")

# Optional data-source / enrichment keys (all degrade gracefully if unset).
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "").strip()
BING_PLACES_API_KEY = os.getenv("BING_PLACES_API_KEY", "").strip()
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "").strip()

DATA_DIR.mkdir(parents=True, exist_ok=True)
