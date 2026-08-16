"""Callback, fallback and error handlers.

Kept separate from `main.py` so the app factory stays thin and every
non-command interaction (inline button presses, plain text, unknown
commands, uncaught errors) has one home.
"""
import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from .common import BACK_KB, MENU_KB, esc

logger = logging.getLogger("nigeria-leads-bot")


async def on_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return
    await q.answer()
    data = q.data or ""
    if data == "menu:home":
        await q.edit_message_text("Main menu", reply_markup=MENU_KB)
        return
    if data == "menu:help":
        from .commands.info import cmd_help
        await q.edit_message_text("Help", parse_mode=ParseMode.HTML)
        await cmd_help(update, ctx)
        return
    if data == "menu:status":
        from .commands.system import cmd_status
        await q.edit_message_text("Status", parse_mode=ParseMode.HTML)
        await cmd_status(update, ctx)
        return
    if data.startswith("export:"):
        from .commands.export import run_export
        fmt = data.split(":", 1)[1]
        await run_export(update, ctx, fmt)
        return
    if data == "menu:find":
        await q.edit_message_text(
            "Use /find &lt;industry&gt; &lt;city&gt; to search.", parse_mode=ParseMode.HTML)
        return
    if data == "menu:packs":
        from .commands.packs import cmd_packs
        await cmd_packs(update, ctx)
        return
    if data == "menu:pipeline":
        from .commands.pipeline import cmd_pipeline
        await cmd_pipeline(update, ctx)
        return
    if data == "menu:campaigns":
        from .commands.campaign import cmd_campaigns
        await cmd_campaigns(update, ctx)
        return
    await q.edit_message_text("Main menu", reply_markup=MENU_KB)


async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    if not text:
        return
    lowered = text.lower()
    if lowered in {"menu", "main menu"}:
        from .commands.info import cmd_menu
        await cmd_menu(update, ctx)
        return
    if lowered in {"help", "commands"}:
        from .commands.info import cmd_help
        await cmd_help(update, ctx)
        return
    if lowered in {"status"}:
        from .commands.system import cmd_status
        await cmd_status(update, ctx)
        return
    await update.message.reply_text(
        f"ℹ️ Type {esc('/')} to see the command menu, or use /help.",
        parse_mode=ParseMode.HTML,
    )


async def on_unknown_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🤔 Unknown command. Try /help for the full list.",
        parse_mode=ParseMode.HTML,
    )


async def on_error(update: object, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled error", exc_info=ctx.error)
    try:
        if update and getattr(update, "effective_message", None):
            await update.effective_message.reply_text(
                "⚠️ Something went wrong. Please try again.")
    except Exception:  # noqa: BLE001
        pass
