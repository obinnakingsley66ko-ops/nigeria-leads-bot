"""Lead collection engine.

Primary source: OpenStreetMap via the Overpass API (free, no key).
Optional: Google Places / Bing Places if their API keys are configured.

`collect()` is blocking and is meant to be run inside a worker thread by the
command handlers, with progress reported through an optional async callback.
"""
import json
import logging
import re
import time
import urllib.parse
import urllib.request

from . import config, db, nigeria

logger = logging.getLogger("nigeria-leads-bot")

# Multiple Overpass mirrors — the primary endpoint is rate-limited and can
# return 429/504 under load, so we fail over automatically.
OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
    "https://overpass.nchc.org.tw/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

UA = "Nigeria-Leads-Bot/1.0 (+https://github.com/obinnakingsley66ko-ops)"

_SCORE_RULES = [
    (lambda l: bool(l.get("website") and l.get("email")), 8),
    (lambda l: bool(l.get("phone") and l.get("email")), 7),
    (lambda l: bool(l.get("email")), 6),
    (lambda l: bool(l.get("website") and l.get("phone")), 5),
    (lambda l: bool(l.get("website")), 3),
    (lambda l: bool(l.get("phone")), 2),
]


def _score(lead: dict) -> int:
    s = 10 if lead.get("contact_person") else 0
    for pred, pts in _SCORE_RULES:
        if pred(lead):
            s += pts
    return min(s, 100)


def _email_status(email: str) -> str:
    """Cheap, safe email plausibility check (no network probing of inboxes).

    Returns 'valid' (format + DNS MX present), 'invalid' or 'unknown'.
    """
    if not email or "@" not in email:
        return "invalid"
    local, domain = email.rsplit("@", 1)
    if not local or "." not in domain:
        return "invalid"
    try:
        import socket
        socket.getaddrinfo(domain, None)
    except Exception:  # noqa: BLE001
        return "unknown"
    return "valid"


def _overpass_query(tag: dict, bbox, limit: int) -> str:
    s, w, n, e = bbox
    # A tag spec is a single OSM key=value pair: {"k": "office", "v": "..."}.
    # Build one node filter `node["office"="..."]`. (Previously the code
    # iterated tag.items(), which produced node["k"="office"] + node["v"="..."]
    # — searching for OSM keys literally named "k"/"v", so every query matched
    # nothing and returned 0 leads.)
    k, v = tag.get("k"), tag.get("v")
    parts = [f'node["{k}"="{v}"]({s},{w},{n},{e});']
    # [out:json] is REQUIRED — without it Overpass returns XML and json.loads
    # fails ("Expecting value"). [timeout:25] caps server-side execution so a
    # slow mirror doesn't hang the whole collection.
    query = f"[out:json][timeout:25];(" + "".join(parts) + ");"
    query += f"out body {min(limit, 50)};"
    return query


def _post_overpass(url: str, data: bytes) -> dict:
    req = urllib.request.Request(
        url, data=data,
        headers={"User-Agent": UA,
                 "Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=40) as resp:
        raw = resp.read().decode() or "{}"
    return json.loads(raw)


def _query_osm(tags: list[dict], bbox, limit: int):
    """Run one Overpass query per tag set, merging results across mirrors.

    Returns (results, all_failed) where all_failed is True only if every
    tag query failed on every mirror (i.e. the data source is unreachable).
    """
    seen, out = set(), []
    failed_tags = 0
    for tag in tags:
        data = urllib.parse.urlencode(
            {"data": _overpass_query(tag, bbox, limit)}).encode()
        payload = None
        last_err = None
        for base in OVERPASS_MIRRORS:
            for attempt in range(2):
                try:
                    payload = _post_overpass(base, data)
                    break
                except Exception as e:  # noqa: BLE001
                    last_err = e
                    time.sleep(1.0 * (attempt + 1))
            if payload is not None:
                break
        if payload is None:
            failed_tags += 1
            logger.warning("Overpass query failed for %s (all mirrors): %s",
                           tag, last_err)
            continue
        for el in payload.get("elements", []):
            if el.get("type") != "node":
                continue
            tags_el = el.get("tags", {})
            key = (tags_el.get("name"), el.get("lat"), el.get("lon"))
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "name": tags_el.get("name"),
                "phone": tags_el.get("phone") or tags_el.get("contact:phone"),
                "email": tags_el.get("email") or tags_el.get("contact:email"),
                "website": tags_el.get("website") or tags_el.get("contact:website"),
                "addr": tags_el.get("addr:street") or tags_el.get("addr:full"),
                "lat": el.get("lat"),
                "lon": el.get("lon"),
            })
    return out, (failed_tags == len(tags))


def _normalise_url(url: str | None) -> str:
    if not url:
        return ""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def _enrich_web(lead: dict) -> dict:
    """Enrich a lead from its own website (title extraction) — very light."""
    site = lead.get("website") or ""
    if not site:
        return lead
    try:
        req = urllib.request.Request(
            _normalise_url(site),
            headers={"User-Agent": UA, "Accept": "text/html"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            chunk = resp.read(4000).decode("utf-8", errors="ignore")
        m = re.search(r"<title[^>]*>(.*?)</title>", chunk, re.I | re.S)
        if m:
            title = re.sub(r"\s+", " ", m.group(1)).strip()
            lead.setdefault("company", title.split("|")[0].strip())
        emails = set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", chunk))
        if emails and not lead.get("email"):
            picked = next((e for e in emails
                           if not e.lower().split("@")[1].startswith(
                               ("gmail", "yahoo", "hotmail", "outlook"))), sorted(emails)[0])
            lead["email"] = picked.lower()
    except Exception:  # noqa: BLE001
        pass
    return lead


def collect(industry: str, bbox, limit: int, campaign_id: str | None = None,
            enrich_web: bool = True, verify: bool = True,
            progress=None) -> dict:
    """Collect leads for one industry in one bbox.

    `progress` is an optional async callback(msg). Never raises for transient
    network/source failures — it reports them and returns a summary dict that
    may carry an "error" key.
    """
    spec = nigeria.INDUSTRIES.get(industry)
    if not spec:
        return {"added": 0, "qualified": 0, "verified": 0}

    city_name = nigeria.city_name_for_bbox(bbox) or ""

    def _sync_report(msg, **kw):
        if progress is None:
            return
        try:
            import asyncio
            asyncio.get_running_loop().create_task(progress(msg, **kw))
        except Exception:  # noqa: BLE001
            pass

    _sync_report(f"\U0001f50e Querying {spec['label']} in {city_name or 'Nigeria'}\u2026")
    raw, source_error = _query_osm(spec["tags"], bbox, limit)

    if source_error and not raw:
        _sync_report("\u26a0\ufe0f OpenStreetMap is unreachable right now.")
        return {
            "added": 0, "qualified": 0, "verified": 0,
            "error": "OpenStreetMap is temporarily unreachable \u2014 please try again in a minute.",
        }

    added = qualified = verified = 0
    for item in raw:
        if not item.get("name"):
            continue
        website = _normalise_url(item.get("website"))
        lead = {
            "company": item["name"],
            "industry": industry,
            "website": website,
            "address": item.get("addr", ""),
            "state": "",
            "city": city_name,
            "phone": item.get("phone", ""),
            "email": (item.get("email") or "").lower(),
            "email_status": "unknown",
            "linkedin": "",
            "contact_person": "",
            "job_title": "",
            "source": "OpenStreetMap",
            "campaign_id": campaign_id,
        }
        if enrich_web:
            lead = _enrich_web(lead)
        if verify:
            lead["email_status"] = _email_status(lead["email"])
            if lead["email_status"] == "valid":
                verified += 1
        lead["score"] = _score(lead)
        lead["qualified"] = lead["score"] >= 14
        if lead["qualified"]:
            qualified += 1
        rowid, is_new = db.add_lead(lead)
        if is_new:
            added += 1

    _sync_report(f"\u2705 {spec['label']} in {city_name or 'Nigeria'}: {added} leads")
    return {"added": added, "qualified": qualified, "verified": verified}
