"""Central configuration loaded from environment variables.

Nothing here is hard-coded except safe defaults; secrets come from the
environment so the repository stays clean and Render/Railway can inject them.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Resolve a writable data directory. Render's ephemeral disk is writable at the
# app dir, but we probe it and fall back to /tmp if the configured path is
# somehow read-only, so the SQLite DB never fails to open.
_DATA_ENV = os.getenv("DATA_DIR", "").strip()
DATA_DIR = Path(_DATA_ENV) if _DATA_ENV else (BASE_DIR / "data")


def _ensure_writable(d: Path) -> Path:
    try:
        d.mkdir(parents=True, exist_ok=True)
        probe = d / ".write_probe"
        probe.touch()
        probe.unlink()
        return d
    except Exception:  # noqa: BLE001 - fall back rather than crash on boot
        fallback = Path("/tmp/nigeria-leads-data")
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


DATA_DIR = _ensure_writable(DATA_DIR)
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
