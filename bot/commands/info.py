"""Welcome / menu / help handlers."""
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from .common import MENU_KB, build_command_list, c, esc

WELCOME = (
    "\ud83d\udc4b <b>Nigeria Leads Bot</b> — your B2B prospecting engine.\n\n"
    "I find, enrich and qualify real Nigerian businesses from public sources "
    "(OpenStreetMap + optional Google/Bing Places), organise them in a CRM "
    "pipeline, and export to CSV, Excel, JSON or your CRM.\n\n"
    "Start with /find construction Lagos or tap a menu button below."
)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    from .. import db, config
    if config.OWNER_ID and not db.get_owner():
        db.set_owner(config.OWNER_ID)
    await update.message.reply_text(WELCOME, parse_mode=ParseMode.HTML,
                                    reply_markup=MENU_KB)


async def cmd_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Main menu", reply_markup=MENU_KB)


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    lines = ["<b>\ud83d\udcd6 Commands</b>", ""]
    for cmd, desc in build_command_list():
        lines.append(f"{c('/' + cmd)} — {esc(desc)}")
    lines += [
        "",
        "Tip: <b>Find</b> uses <code>/find &lt;industry&gt; &lt;city&gt;</code>, "
        "e.g. /find construction Lagos.",
        "Tip: <b>Intel</b> needs a lead id, e.g. /intel 12.",
        "Tip: <b>Stage</b> moves a lead, e.g. /stage 12 Won.",
    ]
    await update.effective_message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
