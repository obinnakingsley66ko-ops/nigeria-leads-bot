"""SQLite persistence layer.

Single source of truth for leads, campaigns, pipeline history and owner
settings. Every write is guarded by a lock so polling/webhook workers can
share the same database file safely.
"""
import threading
from contextlib import contextmanager
from datetime import datetime, timezone

from . import config

_lock = threading.Lock()

STAGES = [
    "New", "Researched", "Contacted", "Follow-up 1", "Follow-up 2",
    "Meeting booked", "Proposal sent", "Won", "Lost",
]

# Column order for the leads table (id is auto-generated).
LEAD_COLS = [
    "company", "industry", "website", "address", "state", "city",
    "phone", "email", "email_status", "linkedin", "contact_person",
    "job_title", "source", "score", "qualified", "pipeline_stage",
    "campaign_id", "added_by", "created_at",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _db():
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = __import__("sqlite3").connect(str(config.DB_PATH), timeout=30)
    conn.row_factory = __import__("sqlite3").Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if they don't exist (idempotent)."""
    with _lock, _db() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                industry TEXT,
                website TEXT,
                address TEXT,
                state TEXT,
                city TEXT,
                phone TEXT,
                email TEXT,
                email_status TEXT DEFAULT 'unknown',
                linkedin TEXT,
                contact_person TEXT,
                job_title TEXT,
                source TEXT DEFAULT 'OpenStreetMap',
                score INTEGER DEFAULT 0,
                qualified INTEGER DEFAULT 0,
                pipeline_stage TEXT DEFAULT 'New',
                campaign_id TEXT,
                added_by INTEGER,
                created_at TEXT,
                UNIQUE(company, city)
            );
            CREATE TABLE IF NOT EXISTS campaigns (
                id TEXT PRIMARY KEY,
                name TEXT,
                industry TEXT,
                location TEXT,
                user_id INTEGER,
                status TEXT DEFAULT 'running',
                total INTEGER DEFAULT 0,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS pipeline_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER,
                stage TEXT,
                note TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )


def add_lead(lead: dict):
    """Insert a lead, skipping exact (company, city) duplicates.

    Returns (rowid, is_new).
    """
    lead = {k: lead.get(k) for k in LEAD_COLS}
    lead["created_at"] = lead.get("created_at") or _now()
    lead["pipeline_stage"] = lead.get("pipeline_stage") or "New"
    lead["source"] = lead.get("source") or "OpenStreetMap"
    lead["score"] = int(lead.get("score") or 0)
    lead["qualified"] = int(bool(lead.get("qualified")))
    values = [lead.get(col) for col in LEAD_COLS]
    cols = ", ".join(LEAD_COLS)
    marks = ", ".join("?" for _ in LEAD_COLS)
    with _lock, _db() as c:
        cur = c.execute(
            f"INSERT OR IGNORE INTO leads ({cols}) VALUES ({marks})", values
        )
        return cur.lastrowid, cur.rowcount > 0


def get_leads(limit: int = 30, industry: str | None = None) -> list[dict]:
    q = "SELECT * FROM leads"
    args: list = []
    if industry:
        q += " WHERE industry = ?"
        args.append(industry)
    q += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    with _db() as c:
        rows = c.execute(q, args).fetchall()
    return [dict(r) for r in rows]


def get_lead(lead_id: int) -> dict | None:
    with _db() as c:
        row = c.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    return dict(row) if row else None


def update_pipeline(lead_id: int, stage: str, note: str | None = None) -> None:
    stage = stage.strip().capitalize()
    with _lock, _db() as c:
        c.execute(
            "UPDATE leads SET pipeline_stage = ? WHERE id = ?", (stage, lead_id)
        )
        c.execute(
            "INSERT INTO pipeline_log (lead_id, stage, note, created_at) "
            "VALUES (?, ?, ?, ?)",
            (lead_id, stage, note, _now()),
        )


def pipeline_counts() -> list[dict]:
    with _db() as c:
        rows = c.execute(
            "SELECT pipeline_stage AS stage, COUNT(*) AS n FROM leads "
            "GROUP BY pipeline_stage ORDER BY n DESC"
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Campaigns
# ---------------------------------------------------------------------------
def create_campaign(camp_id: str, name: str, industry: str, location: str,
                    user_id: int) -> None:
    with _lock, _db() as c:
        c.execute(
            "INSERT OR REPLACE INTO campaigns "
            "(id, name, industry, location, user_id, status, total, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (camp_id, name, industry, location, user_id, "running", 0, _now()),
        )


def finish_campaign(camp_id: str) -> None:
    with _lock, _db() as c:
        c.execute(
            "UPDATE campaigns SET status = 'done', "
            "total = (SELECT COUNT(*) FROM leads WHERE campaign_id = ?) "
            "WHERE id = ?",
            (camp_id, camp_id),
        )


def list_campaigns() -> list[dict]:
    with _db() as c:
        rows = c.execute(
            "SELECT * FROM campaigns ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Stats / owner
# ---------------------------------------------------------------------------
def get_stats() -> dict:
    with _db() as c:
        total = c.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        qualified = c.execute(
            "SELECT COUNT(*) FROM leads WHERE qualified = 1"
        ).fetchone()[0]
        verified = c.execute(
            "SELECT COUNT(*) FROM leads WHERE email_status IN "
            "('valid', 'deliverable')"
        ).fetchone()[0]
        by_industry = [
            dict(r) for r in c.execute(
                "SELECT industry, COUNT(*) AS n FROM leads GROUP BY industry "
                "ORDER BY n DESC"
            ).fetchall()
        ]
        by_city = [
            dict(r) for r in c.execute(
                "SELECT city, COUNT(*) AS n FROM leads GROUP BY city "
                "ORDER BY n DESC"
            ).fetchall()
        ]
    return {
        "total": total,
        "qualified": qualified,
        "verified": verified,
        "by_industry": by_industry,
        "by_city": by_city,
    }


def get_owner() -> int:
    with _db() as c:
        row = c.execute(
            "SELECT value FROM settings WHERE key = 'owner_id'"
        ).fetchone()
    if row and row["value"]:
        return int(row["value"])
    return config.OWNER_ID


def set_owner(uid: int) -> None:
    with _lock, _db() as c:
        c.execute(
            "INSERT INTO settings (key, value) VALUES ('owner_id', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (str(uid),),
        )


def migrate_owner(old_uid: int, new_uid: int) -> None:
    with _lock, _db() as c:
        c.execute("UPDATE leads SET added_by = ? WHERE added_by = ?",
                  (new_uid, old_uid))
        c.execute("UPDATE campaigns SET user_id = ? WHERE user_id = ?",
                  (new_uid, old_uid))
    set_owner(new_uid)
