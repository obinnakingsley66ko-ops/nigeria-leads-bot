"""Campaign handlers: /campaign (create + run) and /campaigns (list)."""
import asyncio
import logging
import uuid

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from .. import collector, db, nigeria
from .common import c, esc

logger = logging.getLogger("nigeria-leads-bot")


async def cmd_campaign(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").replace("/campaign", "", 1).strip()
    parts = [p.strip() for p in text.split("|") if p.strip()]
    if len(parts) < 2:
        await update.message.reply_text(
            "Usage: " + c("/campaign <name> | <industry> | <city>") + "\n"
            "e.g. " + c("/campaign Lagos Construction | construction | Lagos"),
            parse_mode=ParseMode.HTML)
        return

    name = parts[0]
    industry = nigeria.resolve_industry(parts[1])
    city_name, bbox = None, None
    if len(parts) >= 3:
        city_name, bbox = nigeria.resolve_city(parts[2])

    if not industry:
        await update.message.reply_text(
            f"\u26a0\ufe0f Unknown industry: {esc(parts[1])}", parse_mode=ParseMode.HTML)
        return

    camp_id = uuid.uuid4().hex[:12]
    db.create_campaign(camp_id, name, industry, city_name or "Nigeria-wide",
                       update.effective_user.id)
    limit = 60
    sent = await update.message.reply_text(
        f"\ud83c\udfaf Campaign <b>{esc(name)}</b> started — collecting "
        f"<b>{esc(industry)}</b> in <b>{esc(city_name or 'Nigeria')}</b>\u2026",
        parse_mode=ParseMode.HTML)

    async def progress(msg, **kw):
        try:
            await sent.edit_text(esc(msg), parse_mode=ParseMode.HTML)
        except TelegramError:
            pass

    targets = [(city_name, bbox)] if bbox else \
        [(c, b) for c, b in list(nigeria.CITIES.items())[:16]]
    per = max(5, limit // max(1, len(targets)))

    total = 0
    errors = 0
    for cname, bb in targets:
        try:
            summary = await asyncio.to_thread(
                collector.collect, industry, bb, per,
                campaign_id=camp_id, enrich_web=True, verify=True,
                progress=progress)
            total += summary["added"]
        except Exception:  # noqa: BLE001
            errors += 1
            logger.exception("campaign city failed: %s", cname)

    db.finish_campaign(camp_id)
    msg = (f"\u2705 Campaign <b>{esc(name)}</b> complete — {total} leads added"
           + (f" ({errors} city errors)" if errors else "") + ".\n"
           + c("/export csv") + " to download · " + c("/pipeline") + " to manage.")
    await sent.edit_text(msg, parse_mode=ParseMode.HTML)


async def cmd_campaigns(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    camps = db.list_campaigns()
    if not camps:
        await update.message.reply_text("No campaigns yet. Use " + c("/campaign"),
                                        parse_mode=ParseMode.HTML)
        return
    lines = ["<b>\ud83c\udfaf Campaigns</b>", ""]
    for camp in camps:
        lines.append(
            f"• <b>{esc(camp['name'])}</b> — {esc(camp['industry'])} @ "
            f"{esc(camp['location'])} ({camp['total']} leads, {esc(camp['status'])})")
    await update.effective_message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
