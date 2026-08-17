"""System / owner / stats / migration handlers."""
import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from .. import config, db
from .common import c, esc, require_owner

logger = logging.getLogger("nigeria-leads-bot")

_OFFERS = {}


def _get_offer(uid: int) -> dict:
    return _OFFERS.get(uid) or {}


def _set_offer(uid: int, offer: dict) -> None:
    _OFFERS[uid] = offer


def _offer_from_db(uid: int) -> str | None:
    with db._db() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (f"offer:{uid}",)
        ).fetchone()
    return row["value"] if row else None


def _offer_stored(uid: int) -> dict:
    import json
    try:
        raw = _offer_from_db(uid)
        if raw:
            return json.loads(raw)
    except Exception:  # noqa: BLE001
        pass
    return _get_offer(uid)


def _save_offer_db(uid: int, offer: dict) -> None:
    import json
    with db._lock, db._db() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (f"offer:{uid}", json.dumps(offer)),
        )


async def cmd_owner(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    current = db.get_owner()
    if current and current != uid:
        await update.message.reply_text("\u26d4 This bot already has an owner.",
                                        parse_mode=ParseMode.HTML)
        return
    db.set_owner(uid)
    await update.message.reply_text(
        f"\u2705 You are now the owner (ID {uid}).", parse_mode=ParseMode.HTML)


async def cmd_migrate(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not require_owner(update):
        return
    text = (update.message.text or "").replace("/migrate", "", 1).strip()
    parts = text.split()
    if len(parts) < 2 or not all(p.isdigit() for p in parts[:2]):
        await update.message.reply_text(
            "Usage: " + c("/migrate <old_id> <new_id>"), parse_mode=ParseMode.HTML)
        return
    old, new = int(parts[0]), int(parts[1])
    db.migrate_owner(old, new)
    await update.message.reply_text(
        f"\u2705 Owner migrated from {old} to {new}.", parse_mode=ParseMode.HTML)


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    import time
    from .common import STARTED_AT
    uptime = int(time.time() - STARTED_AT.timestamp())
    m, s = divmod(uptime, 60)
    h, m = divmod(m, 60)
    stats = db.get_stats()
    owner = db.get_owner()
    sources = "OpenStreetMap (primary)"
    if config.GOOGLE_PLACES_API_KEY:
        sources += " + Google Places"
    if config.BING_PLACES_API_KEY:
        sources += " + Bing Places"
    lines = [
        "\ud83d\udce1 <b>Bot status</b>",
        f"Owner: {owner or 'unset'}",
        f"Uptime: {h}h {m}m {s}s",
        f"Data sources: {esc(sources)}",
        f"Storage: {esc(str(config.DB_PATH))}",
        f"Leads: {stats['total']} · qualified {stats['qualified']} · "
        f"verified emails {stats['verified']}",
    ]
    await update.effective_message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not require_owner(update):
        return
    stats = db.get_stats()
    lines = [f"\ud83d\udcca <b>Database stats</b> — {stats['total']} leads",
             f"Qualified: {stats['qualified']} · Verified emails: {stats['verified']}",
             "", "<b>By industry</b>"]
    for row in stats["by_industry"][:10]:
        lines.append(f"• {esc(row['industry'] or '—')}: {row['n']}")
    lines.append("")
    lines.append("<b>By city</b>")
    for row in stats["by_city"][:10]:
        lines.append(f"• {esc(row['city'] or '—')}: {row['n']}")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_offer(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Set a one-time introduction used by /intel outreach assets.

    Usage: /offer Company | industry | Your Name | phone
    """
    text = (update.message.text or "").replace("/offer", "", 1).strip()
    parts = [p.strip() for p in text.split("|") if p.strip()]
    if len(parts) < 3:
        await update.message.reply_text(
            "Usage: " + c("/offer Company | industry | Your Name | phone"),
            parse_mode=ParseMode.HTML)
        return
    company, industry, you = parts[0], parts[1], parts[2]
    phone = parts[3] if len(parts) > 3 else ""
    offer = {"company": company, "industry": industry, "you": you, "phone": phone}
    _set_offer(update.effective_user.id, offer)
    _save_offer_db(update.effective_user.id, offer)
    await update.message.reply_text(
        f"\u2705 Introduction saved for outreach assets (Hi, I'm {esc(you)} from {esc(company)}).",
        parse_mode=ParseMode.HTML)
