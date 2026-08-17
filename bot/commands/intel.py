"""Sales intel + outreach asset generation for a single lead."""
import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from .. import db
from .common import a, c, esc

logger = logging.getLogger("nigeria-leads-bot")

EMAIL_TEMPLATE = (
    "Subject: {subject}\n\nHi {name},\n\nI noticed {company} ({industry}) and "
    "wanted to reach out about how we help Nigerian businesses like yours "
    "streamline operations and win more clients.\n\nWould you be open to a "
    "quick chat this week?\n\nBest,\n{you}\n{phone}"
)

CALL_TEMPLATE = (
    "\ud83d\udcde <b>Call script</b>\n"
    "1. Intro: \"Hi {name}, this is {you}. I help {industry} businesses in "
    "{city} grow.\"\n"
    "2. Hook: \"I saw {company}'s work and have one idea for {city}.\"\n"
    "3. Qualify: \"What's the biggest challenge right now?\"\n"
    "4. Pitch: \"We solve exactly that — 15-minute demo?\"\n"
    "5. Objection: \"No budget?\" → \"Let's start small, one low-risk pilot.\""
)


def _offer(uid) -> dict:
    from .system import _offer_stored
    return _offer_stored(uid)


async def cmd_intel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").replace("/intel", "", 1).strip()
    if not text or not text.isdigit():
        await update.effective_message.reply_text("Usage: " + c("/intel <lead_id>"),
                                        parse_mode=ParseMode.HTML)
        return
    lead = db.get_lead(int(text))
    if not lead:
        await update.effective_message.reply_text(f"\u26a0\ufe0f Lead {text} not found.",
                                        parse_mode=ParseMode.HTML)
        return
    site = a(lead["website"], "website") if lead["website"] else "no website"
    lines = [
        f"\ud83e\udde0 <b>Intel: {esc(lead['company'])}</b> {c(lead['id'])}",
        f"\ud83c\udfed {esc(lead['industry'] or '—')} · \ud83d\udccd {esc(lead['city'] or '—')}",
        f"\ud83c\udf10 {site} · \u2b50 {lead['score']} pts · {esc(lead['pipeline_stage'] or 'New')}",
        f"\ud83d\udce7 {esc(lead['email'] or '—')} ({esc(lead['email_status'] or 'unknown')})",
        f"\ud83d\udcde {esc(lead['phone'] or '—')}",
        "",
        "<b>Outreach assets</b>",
    ]
    offer = _offer(update.effective_user.id)
    you = offer.get("you") or "Your Name"
    name = (lead.get("contact_person") or "there")
    if lead.get("email"):
        email = EMAIL_TEMPLATE.format(
            subject=f"Quick idea for {lead['company']}",
            name=name, company=lead["company"], industry=lead["industry"] or "your sector",
            you=you, phone=offer.get("phone") or "")
        lines.append(f"\u2709\ufe0f <b>Cold email</b>\n<code>{esc(email)}</code>")
    lines.append(CALL_TEMPLATE.format(
        name=name, you=you, industry=lead["industry"] or "your sector",
        city=lead["city"] or "your city", company=lead["company"]))
    await update.effective_message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
