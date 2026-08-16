"""Prospect packs: one-click pre-scoped lead searches.

Each pack is a curated (industry, city) pair with a friendly label. Packs run
through the same collector and are therefore deduplicated and stored in the
same database.
"""
import asyncio
import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from .. import collector, nigeria
from .common import c, esc

logger = logging.getLogger("nigeria-leads-bot")

PACKS = {
    "Construction in Lagos": ("construction", "lagos"),
    "Accounting in Abuja": ("accounting", "abuja"),
    "Hospitals in Benin City": ("hospitals", "benin_city"),
    "Real Estate in Port Harcourt": ("real_estate", "port_harcourt"),
    "Logistics in Kano": ("logistics", "kano"),
    "Hotels in Lagos": ("hotels", "lagos"),
    "Restaurants in Abuja": ("restaurants", "abuja"),
    "Law Firms in Lagos": ("law", "lagos"),
    "Schools in Ibadan": ("schools", "ibadan"),
    "Tech in Lagos": ("tech", "lagos"),
}


async def _run_pack(update, sent, name, industry, city_key, limit=40):
    async def progress(msg, **kw):
        try:
            await sent.edit_text(esc(msg), parse_mode=ParseMode.HTML)
        except TelegramError:
            pass

    city_name = nigeria.CITY_NAMES.get(city_key, city_key) if city_key else "Nigeria"
    if city_key:
        _, bbox = nigeria.resolve_city(city_key)
    else:
        bbox = None

    total = 0
    if bbox:
        summary = await asyncio.to_thread(
            collector.collect, industry, bbox, limit, enrich_web=True,
            verify=True, progress=progress)
        total = summary["added"]
    else:
        for ck, bb in list(nigeria.CITIES.items())[:8]:
            try:
                summary = await asyncio.to_thread(
                    collector.collect, industry, bb, max(5, limit // 8),
                    enrich_web=True, verify=True, progress=progress)
                total += summary["added"]
            except Exception:  # noqa: BLE001
                continue

    await sent.edit_text(
        f"✅ <b>{esc(name)}</b>: {total} new leads collected.\n"
        f"{c('/export csv')} to download · {c('/pipeline')} to manage.",
        parse_mode=ParseMode.HTML)


async def cmd_packs(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(name, callback_data=f"pack:{name}")]
        for name in PACKS
    ])
    ctx.user_data["packs"] = PACKS
    await update.message.reply_text(
        "📦 <b>Prospect packs</b> — pick one:", parse_mode=ParseMode.HTML,
        reply_markup=kb)


async def run_pack_callback(update, ctx, name: str) -> None:
    packs = ctx.user_data.get("packs") or PACKS
    if name not in packs:
        await update.callback_query.edit_message_text("Pack not found.")
        return
    industry, city_key = packs[name]
    await update.callback_query.answer()
    sent = await update.callback_query.edit_message_text(
        f"🔎 Running <b>{esc(name)}</b>…", parse_mode=ParseMode.HTML)
    await _run_pack(update, sent, name, industry, city_key)
