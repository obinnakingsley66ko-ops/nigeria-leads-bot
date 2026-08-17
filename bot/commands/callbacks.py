"""Callback, fallback and error handlers.

Kept separate from `main.py` so the app factory stays thin and every
non-command interaction (inline button presses, plain text, unknown
commands, uncaught errors) has one home.

NOTE: this module lives INSIDE `bot/commands/`, so sibling imports are
relative to this package (e.g. `from .info import ...`), NOT
`from .commands.info import ...`.
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
        from .info import cmd_help
        await cmd_help(update, ctx)
        return
    if data == "menu:status":
        from .system import cmd_status
        await cmd_status(update, ctx)
        return
    if data.startswith("export:"):
        from .export import run_export
        fmt = data.split(":", 1)[1]
        await run_export(update, ctx, fmt)
        return
    if data == "menu:find":
        await q.edit_message_text(
            "Use /find &lt;industry&gt; &lt;city&gt; to search.", parse_mode=ParseMode.HTML)
        return
    if data == "menu:packs":
        from .packs import cmd_packs
        await cmd_packs(update, ctx)
        return
    if data == "menu:pipeline":
        from .pipeline import cmd_pipeline
        await cmd_pipeline(update, ctx)
        return
    if data == "menu:campaigns":
        from .campaign import cmd_campaigns
        await cmd_campaigns(update, ctx)
        return
    if data == "menu:export":
        from .common import EXPORT_KB
        await q.edit_message_text("📤 <b>Export format</b>:", parse_mode=ParseMode.HTML,
                                  reply_markup=EXPORT_KB)
        return
    if data.startswith("pack:"):
        from .packs import run_pack_callback
        await run_pack_callback(update, ctx, data.split(":", 1)[1])
        return
    await q.edit_message_text("Main menu", reply_markup=MENU_KB)


async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    if not text:
        return
    lowered = text.lower()
    if lowered in {"menu", "main menu"}:
        from .info import cmd_menu
        await cmd_menu(update, ctx)
        return
    if lowered in {"help", "commands"}:
        from .info import cmd_help
        await cmd_help(update, ctx)
        return
    if lowered in {"status"}:
        from .system import cmd_status
        await cmd_status(update, ctx)
        return
    await update.message.reply_text(
        f"\u2139\ufe0f Type {esc('/')} to see the command menu, or use /help.",
        parse_mode=ParseMode.HTML,
    )


async def on_unknown_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "\ud83e\udd14 Unknown command. Try /help for the full list.",
        parse_mode=ParseMode.HTML,
    )


async def on_error(update: object, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled error", exc_info=ctx.error)
    try:
        if update and getattr(update, "effective_message", None):
            await update.effective_message.reply_text(
                "\u26a0\ufe0f Something went wrong. Please try again.")
    except Exception:  # noqa: BLE001
        pass
