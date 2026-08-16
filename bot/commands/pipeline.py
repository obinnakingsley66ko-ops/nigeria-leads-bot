"""CRM pipeline handlers: /pipeline, /stages, /stage, /leads."""
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from .. import db
from .common import c, esc

STAGE_ORDER = [
    "New", "Researched", "Contacted", "Follow-up 1", "Follow-up 2",
    "Meeting booked", "Proposal sent", "Won", "Lost",
]


async def cmd_pipeline(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    counts = db.pipeline_counts()
    total = sum(r["n"] for r in counts)
    lines = [f"📊 <b>Pipeline</b> — {total} leads", ""]
    for stage in STAGE_ORDER:
        n = next((r["n"] for r in counts if r["stage"] == stage), 0)
        bar = "▰" * min(10, n) + "▱" * (10 - min(10, n))
        lines.append(f"{esc(stage):<16} {bar} {n}")
    lines += ["", c("/leads") + " recent · " + c("/stage <id> <stage>") + " to move"]
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_stages(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📋 <b>Stages</b>: " + " → ".join(esc(s) for s in STAGE_ORDER),
        parse_mode=ParseMode.HTML)


async def cmd_stage(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").replace("/stage", "", 1).strip()
    parts = text.split(None, 1)
    if not parts or not parts[0].isdigit():
        await update.message.reply_text(
            "Usage: " + c("/stage <lead_id> <stage>") + "\ne.g. /stage 12 Won",
            parse_mode=ParseMode.HTML)
        return
    lead_id = int(parts[0])
    stage = parts[1].strip() if len(parts) > 1 else ""
    if not stage:
        await update.message.reply_text("Please include a stage, e.g. /stage 12 Won.",
                                        parse_mode=ParseMode.HTML)
        return
    match = next((s for s in STAGE_ORDER if s.lower() == stage.lower()), None)
    if not match:
        await update.message.reply_text(
            "Valid stages: " + ", ".join(STAGE_ORDER), parse_mode=ParseMode.HTML)
        return
    lead = db.get_lead(lead_id)
    if not lead:
        await update.message.reply_text(f"⚠️ Lead {lead_id} not found.",
                                        parse_mode=ParseMode.HTML)
        return
    db.update_pipeline(lead_id, match, note=f"moved by {update.effective_user.id}")
    await update.message.reply_text(
        f"✅ Lead {lead_id} ({esc(lead['company'])}) → {esc(match)}",
        parse_mode=ParseMode.HTML)


async def cmd_leads(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    from .common import fmt_leads
    leads = db.get_leads(limit=10)
    if not leads:
        await update.message.reply_text("No leads yet. Try /find construction Lagos.",
                                        parse_mode=ParseMode.HTML)
        return
    await update.message.reply_text(fmt_leads(leads, "Recent leads"),
                                    parse_mode=ParseMode.HTML)
