"""Nigeria B2B Lead Gen — application entrypoint.

This module is now a THIN factory: all command logic lives in `bot/commands/`
(one file per concern). It only wires logging, the command registry, the
callback/fallback/error handlers, and the polling/webhook run loops.

Run with:
    python -m bot.main                 # long-polling (default)
    WEBHOOK_URL=... python -m bot.main # webhook mode (Render/Railway)
"""
import logging
import sys
from logging.handlers import RotatingFileHandler

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters,
)

from . import config, db
from .commands import COMMANDS, on_button, on_error, on_text, on_unknown_command
from .commands.common import build_command_list

# ---------------------------------------------------------------------------
# Logging (console + rotating file)
# ---------------------------------------------------------------------------
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
_handlers = [logging.StreamHandler(sys.stdout)]
try:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    _fh = RotatingFileHandler(
        config.DATA_DIR / "bot.log", maxBytes=2_000_000, backupCount=3,
        encoding="utf-8",
    )
    _fh.setFormatter(logging.Formatter(LOG_FORMAT))
    _handlers.append(_fh)
except Exception:  # never let logging setup crash the bot
    pass

logging.basicConfig(format=LOG_FORMAT, level=logging.INFO, handlers=_handlers)
logger = logging.getLogger("nigeria-leads-bot")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.INFO)


async def _install_commands(app: Application) -> None:
    """Register the native Telegram command menu (the '/' button)."""
    try:
        await app.bot.set_my_commands(build_command_list())
    except Exception as e:  # noqa: BLE001
        logger.warning("set_my_commands failed: %s", e)


def build_app() -> Application:
    """Construct and fully wire the Application (no network I/O yet)."""
    db.init_db()
    builder = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN)

    if config.WEBHOOK_URL:
        builder.updater(None)  # webhook mode doesn't need a polling updater

    app = builder.post_init(_install_commands).build()

    # Register all command handlers from the central registry.
    for name, handler in COMMANDS.items():
        app.add_handler(CommandHandler(name, handler))

    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.COMMAND, on_unknown_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_error_handler(on_error)
    return app


# ---------------------------------------------------------------------------
# Entrypoint: webhook or resilient polling
# ---------------------------------------------------------------------------
def _run_webhook(app: Application) -> None:
    url = config.WEBHOOK_URL.rstrip("/") + config.WEBHOOK_PATH
    logger.info("Starting webhook at %s (port %s)", url, config.PORT)
    app.run_webhook(
        listen="0.0.0.0",
        port=config.PORT,
        url_path=config.WEBHOOK_PATH,
        webhook_url=url,
        drop_pending_updates=True,
    )


def _run_polling(app: Application) -> None:
    logger.info("Starting long-polling (owner ID: %s)", config.OWNER_ID)
    app.run_polling(drop_pending_updates=False, allowed_updates=Update.ALL_TYPES)


def main() -> None:
    app = build_app()
    logger.info("Nigeria B2B Lead Gen bot booting.")
    logger.info("Data sources: OpenStreetMap (primary) + optional Google/Bing Places.")
    logger.info("Storage: %s", config.DB_PATH)

    if config.WEBHOOK_URL:
        _run_webhook(app)
        return
    _run_polling(app)


if __name__ == "__main__":
    main()
