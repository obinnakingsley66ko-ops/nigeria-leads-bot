"""Lead discovery handlers: /find and /search.

Both collect real leads from OpenStreetMap (plus optional Google/Bing Places)
via `collector.collect`, running blocking work in a worker thread so the event
loop never stalls. Progress is throttled to avoid flooding Telegram edits.
"""
import asyncio
import logging
import time

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from .. import collector, db, nigeria
from .common import c, esc, fmt_leads

logger = logging.getLogger("nigeria-leads-bot")


async def _run_collection(update, sent, industry, bbox, limit, campaign_id=None):
    """Run collector.collect in a thread, editing `sent` with throttled progress.

    Returns the summary dict or None on failure (after editing `sent`).
    """
    last_edit = [0.0]

    async def progress(msg, **kw):
        now = time.time()
        if now - last_edit[0] < 1.5 and not msg.startswith(("✅", "❌")):
            return
        last_edit[0] = now
        try:
            await sent.edit_text(esc(msg), parse_mode=ParseMode.HTML)
        except TelegramError:
            pass

    try:
        return await asyncio.to_thread(
            collector.collect, industry, bbox, limit,
            campaign_id=campaign_id, enrich_web=True, verify=True,
            progress=progress)
    except Exception as e:  # noqa: BLE001
        logger.exception("collection failed for industry=%s", industry)
        try:
            await sent.edit_text(f"❌ Search failed: {esc(e)}",
                                 parse_mode=ParseMode.HTML)
        except TelegramError:
            pass
        return None


async def cmd_find(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").replace("/find", "", 1).strip()
    from .common import parse_industry_city
    industry, city = parse_industry_city(text)

    if not industry:
        await update.message.reply_text(
            "⚠️ Unknown industry. Try " + c("/find construction Lagos") +
            "\nSee " + c("/packs") + " for supported industries.",
            parse_mode=ParseMode.HTML)
        return
    if not city:
        await update.message.reply_text(
            "⚠️ Please specify a city, e.g. " + c("/find construction Lagos") +
            "\nSupported: Lagos, Abuja, Port Harcourt, Benin City, Kano, "
            "Ibadan, Enugu, Aba, Onitsha, Warri, Uyo, Calabar, Kaduna, Jos…",
            parse_mode=ParseMode.HTML)
        return

    city_name, bbox = nigeria.resolve_city(city)
    if not bbox:
        await update.message.reply_text(f"⚠️ Unknown city: {esc(city)}",
                                        parse_mode=ParseMode.HTML)
        return

    limit = 30
    label = nigeria.INDUSTRIES.get(industry, {}).get("label", industry)
    sent = await update.message.reply_text(
        f"🔎 Searching <b>{esc(label)}</b> in <b>{esc(city_name)}</b>… "
        f"(real data, ~{limit} leads)", parse_mode=ParseMode.HTML)

    summary = await _run_collection(update, sent, industry, bbox, limit)
    if summary is None:
        return

    leads = db.get_leads(limit=limit, industry=industry)
    top = leads[:6]
    lines = [
        f"✅ <b>Done — {summary['added']} leads</b> "
        f"(qualified: {summary['qualified']}, verified emails: {summary['verified']})",
        "", fmt_leads(top, "Top results"),
        "",
        f"{c('/export csv')} to download · {c('/intel <id>')} for outreach "
        f"· {c('/pipeline')} to manage",
    ]
    await sent.edit_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_search(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").replace("/search", "", 1).strip()
    industry = nigeria.resolve_industry(text)
    if not industry:
        await update.message.reply_text("⚠️ Unknown industry.",
                                        parse_mode=ParseMode.HTML)
        return

    sent = await update.message.reply_text(
        f"🔎 Searching <b>{esc(industry)}</b> across Nigeria (top cities)…",
        parse_mode=ParseMode.HTML)

    async def progress(msg, **kw):
        try:
            await sent.edit_text(esc(msg), parse_mode=ParseMode.HTML)
        except TelegramError:
            pass

    total = 0
    for _city, bbox in list(nigeria.CITIES.items())[:16]:
        try:
            summary = await asyncio.to_thread(
                collector.collect, industry, bbox, 10,
                enrich_web=True, verify=True, progress=progress)
            total += summary["added"]
        except Exception:  # noqa: BLE001
            continue

    await sent.edit_text(
        f"✅ Collected <b>{total}</b> leads for <b>{esc(industry)}</b> across Nigeria.\n"
        + c("/export csv") + " to download.", parse_mode=ParseMode.HTML)
