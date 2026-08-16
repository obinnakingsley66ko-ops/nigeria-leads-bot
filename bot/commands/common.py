"""Shared helpers for all command handlers.

This module is the single source of truth for HTML-escaping, keyboard/menu
definitions, owner access checks, industry/city parsing, lead formatting and
the command list. Every handler imports from here so there is exactly ONE
implementation of each shared concern.
"""
import html
from datetime import datetime, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

from .. import config, db, nigeria


# Process start time (used for uptime reporting).
STARTED_AT = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# HTML helpers (single source of truth for escaping)
# ---------------------------------------------------------------------------
def esc(s) -> str:
    """Escape arbitrary user/data text for HTML parse_mode."""
    if s is None:
        return ""
    return html.escape(str(s), quote=False)


def b(s) -> str:
    return f"<b>{esc(s)}</b>"


def c(s) -> str:
    return f"<code>{esc(s)}</code>"


def a(url, label) -> str:
    """Build a safe <a href> link (HTML parse mode)."""
    return f'<a href="{esc(url)}">{esc(label)}</a>'


# ---------------------------------------------------------------------------
# Menus / keyboards
# ---------------------------------------------------------------------------
MENU_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔎 Find leads", callback_data="menu:find"),
     InlineKeyboardButton("📦 Prospect packs", callback_data="menu:packs")],
    [InlineKeyboardButton("📊 Pipeline", callback_data="menu:pipeline"),
     InlineKeyboardButton("🎯 Campaigns", callback_data="menu:campaigns")],
    [InlineKeyboardButton("📥 Export", callback_data="menu:export"),
     InlineKeyboardButton("ℹ️ Help", callback_data="menu:help")],
    [InlineKeyboardButton("🩺 Status", callback_data="menu:status")],
])

EXPORT_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("CSV", callback_data="export:csv"),
     InlineKeyboardButton("Excel", callback_data="export:xlsx"),
     InlineKeyboardButton("JSON", callback_data="export:json")],
    [InlineKeyboardButton("HubSpot", callback_data="export:hubspot"),
     InlineKeyboardButton("GoHighLevel", callback_data="export:gohighlevel"),
     InlineKeyboardButton("Pipedrive", callback_data="export:pipedrive")],
])

BACK_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("◀️ Back to menu", callback_data="menu:home")],
])


# ---------------------------------------------------------------------------
# Command list (native Telegram '/' menu)
# ---------------------------------------------------------------------------
def build_command_list() -> list:
    """Return the list of (command, description) pairs for set_my_commands."""
    return [
        ("start", "Start / welcome"),
        ("menu", "Main menu"),
        ("help", "All commands"),
        ("status", "Bot + data-source status"),
        ("find", "Find leads — /find construction Lagos"),
        ("packs", "One-click prospect packs"),
        ("campaign", "Create + run a campaign"),
        ("campaigns", "List campaigns"),
        ("pipeline", "CRM pipeline stages"),
        ("stage", "Move a lead — /stage 12 Won"),
        ("leads", "Recent leads"),
        ("intel", "Sales intel + outreach — /intel 12"),
        ("export", "Download leads (csv/xlsx/json/crm)"),
        ("stats", "Database stats (owner)"),
        ("owner", "Confirm owner (owner)"),
    ]


# ---------------------------------------------------------------------------
# Owner / access helpers
# ---------------------------------------------------------------------------
def is_owner(update: Update) -> bool:
    return bool(update.effective_user and update.effective_user.id == config.OWNER_ID)


def require_owner(update: Update) -> bool:
    """Return True if the caller is the owner; otherwise reply and return False."""
    if is_owner(update):
        return True
    if update.effective_message:
        try:
            update.effective_message.reply_text("⛔ This command is owner-only.")
        except Exception:  # noqa: BLE001
            pass
    return False


# ---------------------------------------------------------------------------
# Parsing helpers (robust, alias-aware)
# ---------------------------------------------------------------------------
def parse_industry_city(text: str):
    """Return (industry_key, city_name) with generous, alias-aware parsing.

    Tries progressively longer industry phrases first, then resolves a city
    from the remaining words. Falls back gracefully when only one of the two
    is present.
    """
    parts = [p.strip() for p in (text or "").split() if p.strip()]
    if not parts:
        return None, None

    industry = None
    city_words = parts
    for n in range(len(parts), 0, -1):
        candidate = nigeria.resolve_industry(" ".join(parts[:n]))
        if candidate:
            industry = candidate
            city_words = parts[n:]
            break
    if industry is None:
        industry = nigeria.resolve_industry(parts[0])
        if industry is None:
            city_words = parts

    city_name = None
    for n in range(len(city_words), 0, -1):
        resolved = nigeria.resolve_city(" ".join(city_words[:n]))
        if resolved:
            city_name = resolved[0]
            break
    return industry, city_name


# ---------------------------------------------------------------------------
# Lead formatting
# ---------------------------------------------------------------------------
def fmt_leads(leads, title="Recent leads") -> str:
    lines = [f"<b>{esc(title)}</b>", ""]
    for lead in leads:
        emoji = "🟢" if lead.get("qualified") else "⚪"
        website = lead.get("website") or ""
        site = a(website, "site") if website else "no site"
        lines.append(
            f"{emoji} <b>{esc((lead.get('company') or '')[:40])}</b> "
            f"{c(lead.get('id'))}\n"
            f"   📍 {esc(lead.get('city') or '—')} | 📞 {esc(lead.get('phone') or '—')} | "
            f"✉️ {esc(lead.get('email') or '—')} "
            f"({esc(lead.get('email_status') or 'unknown')})\n"
            f"   ⭐ {lead.get('score', 0)} pts · {esc(lead.get('pipeline_stage') or 'New')} · {site}"
        )
    return "\n".join(lines)
