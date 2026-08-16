"""Command handler registry.

Central mapping of command name -> handler function. `main.py` imports this
single dict to register every handler, keeping routing fully declarative.
"""
from .callbacks import on_button, on_error, on_text, on_unknown_command
from .campaign import cmd_campaign, cmd_campaigns
from .export import cmd_export
from .find import cmd_find, cmd_search
from .info import cmd_help, cmd_menu, cmd_start
from .intel import cmd_intel
from .packs import cmd_packs
from .pipeline import cmd_leads, cmd_pipeline, cmd_stage, cmd_stages
from .system import cmd_migrate, cmd_owner, cmd_stats, cmd_status

# Ordered command -> handler mapping (order controls '/' autocomplete order).
COMMANDS = {
    "start": cmd_start,
    "menu": cmd_menu,
    "help": cmd_help,
    "status": cmd_status,
    "owner": cmd_owner,
    "migrate": cmd_migrate,
    "stats": cmd_stats,
    "find": cmd_find,
    "search": cmd_search,
    "packs": cmd_packs,
    "campaign": cmd_campaign,
    "campaigns": cmd_campaigns,
    "pipeline": cmd_pipeline,
    "stages": cmd_stages,
    "stage": cmd_stage,
    "leads": cmd_leads,
    "intel": cmd_intel,
    "export": cmd_export,
}

__all__ = [
    "COMMANDS",
    "on_button",
    "on_error",
    "on_text",
    "on_unknown_command",
]
