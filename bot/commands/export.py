"""Export handlers: CSV / Excel / JSON / CRM-ready formats.

All exports read straight from the SQLite database so they always reflect the
latest leads.
"""
import csv
import io
import json
import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from .. import db
from .common import c, esc

logger = logging.getLogger("nigeria-leads-bot")

_FIELDS = [
    "id", "company", "industry", "website", "address", "state", "city",
    "phone", "email", "email_status", "linkedin", "contact_person",
    "job_title", "source", "score", "qualified", "pipeline_stage",
    "campaign_id", "created_at",
]


def _rows():
    for lead in db.get_leads(limit=100000):
        yield {k: lead.get(k, "") for k in _FIELDS}


def _csv_bytes() -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=_FIELDS)
    w.writeheader()
    for r in _rows():
        w.writerow({k: (v if v is not None else "") for k, v in r.items()})
    return buf.getvalue().encode("utf-8-sig")


def _json_bytes() -> bytes:
    return json.dumps(list(_rows()), ensure_ascii=False, indent=2).encode("utf-8")


def _hubspot_bytes() -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Company Name", "Industry", "Website URL", "Phone Number",
                "Email", "City", "State", "Address", "Contact Firstname",
                "Job Title"])
    for r in _rows():
        contact = (r.get("contact_person") or " ").split(" ", 1)
        first = contact[0]
        w.writerow([r.get("company", ""), r.get("industry", ""),
                    r.get("website", ""), r.get("phone", ""),
                    r.get("email", ""), r.get("city", ""), r.get("state", ""),
                    r.get("address", ""), first, r.get("job_title", "")])
    return buf.getvalue().encode("utf-8-sig")


def _gohighlevel_bytes() -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Name", "Phone", "Email", "Company", "Website", "City",
                "State", "Address", "Tags"])
    for r in _rows():
        w.writerow([r.get("contact_person") or r.get("company", ""),
                    r.get("phone", ""), r.get("email", ""),
                    r.get("company", ""), r.get("website", ""),
                    r.get("city", ""), r.get("state", ""),
                    r.get("address", ""), "nigeria-leads"])
    return buf.getvalue().encode("utf-8-sig")


def _pipedrive_bytes() -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Title", "Person", "Email", "Phone", "Value", "Stage"])
    for r in _rows():
        w.writerow([r.get("company", ""), r.get("contact_person", ""),
                    r.get("email", ""), r.get("phone", ""), "",
                    r.get("pipeline_stage", "New")])
    return buf.getvalue().encode("utf-8-sig")


def _google_sheets_bytes() -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter="\t")
    w.writerow(_FIELDS)
    for r in _rows():
        w.writerow([r.get(k, "") for k in _FIELDS])
    return buf.getvalue().encode("utf-8")


EXPORTERS = {
    "csv": ("leads.csv", _csv_bytes),
    "xlsx": ("leads.csv", _csv_bytes),
    "json": ("leads.json", _json_bytes),
    "hubspot": ("leads_hubspot.csv", _hubspot_bytes),
    "gohighlevel": ("leads_gohighlevel.csv", _gohighlevel_bytes),
    "pipedrive": ("leads_pipedrive.csv", _pipedrive_bytes),
    "google_sheets": ("leads_google_sheets.tsv", _google_sheets_bytes),
}


def _export_doc(fmt: str) -> tuple[str, bytes] | None:
    if fmt in EXPORTERS:
        name, fn = EXPORTERS[fmt]
        return name, fn()
    return None


async def run_export(update: Update, ctx: ContextTypes.DEFAULT_TYPE,
                     fmt: str) -> None:
    fmt = (fmt or "").lower()
    doc = _export_doc(fmt)
    if not doc:
        await update.effective_message.reply_text("Unknown export format.", parse_mode=ParseMode.HTML)
        return
    name, data = doc
    total = db.get_stats()["total"]
    if not data or not data.strip():
        await update.effective_message.reply_text("No leads to export yet.",
                                        parse_mode=ParseMode.HTML)
        return
    await update.effective_message.reply_document(
        document=io.BytesIO(data), filename=name,
        caption=f"\u2705 {total} leads exported ({fmt.upper()})")


async def cmd_export(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").replace("/export", "", 1).strip().lower()
    from .common import EXPORT_KB
    if not text:
        await update.message.reply_text("\ud83d\udce4 <b>Export format</b>:",
                                        parse_mode=ParseMode.HTML,
                                        reply_markup=EXPORT_KB)
        return
    await run_export(update, ctx, text)
