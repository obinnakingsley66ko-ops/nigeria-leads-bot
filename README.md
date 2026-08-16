# Nigeria Leads Bot

A Telegram B2B lead-generation bot (`@LeedAibot`) that discovers, enriches,
qualifies, organises and exports Nigerian business leads from legal public
sources.

## Features

- **Real discovery** — OpenStreetMap/Overpass (primary), optional Google/Bing Places.
- **Nigeria coverage** — 15+ major cities (Lagos, Abuja, Port Harcourt, Benin City,
  Kano, Ibadan, Enugu, Aba, Onitsha, Warri, Uyo, Calabar, Kaduna, Jos…) and 36 states.
- **Industries** — construction, real estate, accounting, law, schools, universities,
  hospitals, clinics, hotels, restaurants, logistics, manufacturing, retail, churches,
  NGOs, tech, SMEs, commercial cleaning.
- **Enrichment** — website title, business-email harvesting + verification,
  lead scoring and qualification.
- **Prospect packs** — one-click pre-scoped searches.
- **CRM pipeline** — `New → Researched → Contacted → … → Won/Lost`.
- **Sales intel** — cold email, call script and LinkedIn note per lead.
- **Campaigns** — multi-city collection with duplicate skipping.
- **Exports** — CSV, Excel (CSV-compatible), JSON, Google Sheets (TSV),
  HubSpot, GoHighLevel, Pipedrive.

## Commands

| Command | Description |
|---|---|
| `/start` | Welcome + menu |
| `/menu` | Inline main menu |
| `/help` | All commands |
| `/status` | Bot + data-source status |
| `/find <industry> <city>` | Discover leads |
| `/search <industry>` | Search top cities |
| `/packs` | One-click prospect packs |
| `/campaign <name> \| <industry> \| <city>` | Create + run campaign |
| `/campaigns` | List campaigns |
| `/pipeline` | CRM stages |
| `/stages` | List stages |
| `/stage <id> <stage>` | Move a lead |
| `/leads` | Recent leads |
| `/intel <id>` | Sales intel + outreach |
| `/export [format]` | CSV/Excel/JSON/CRM |
| `/stats` | Database stats (owner) |
| `/owner` | Claim ownership |
| `/migrate <old> <new>` | Migrate owner (owner) |
| `/offer …` | Set outreach introduction |

## Run locally

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill TELEGRAM_BOT_TOKEN + OWNER_ID
python -m bot.main     # long-polling
```

To use webhook mode (Render/Railway), set `WEBHOOK_URL` in `.env`.

## Deploy

- **Render**: create a Background Worker (Docker) → set `TELEGRAM_BOT_TOKEN`
  and `OWNER_ID` → deploy. (Or use the included `render.yaml` Blueprint.)
- **Railway**: connect repo → add env vars → deploy.
- **Docker**: `docker build -t nigeria-leads-bot . && docker run --env-file .env nigeria-leads-bot`

## Architecture

```
bot/
  main.py            # thin app factory + polling/webhook loops
  config.py          # env-driven config
  db.py              # SQLite persistence
  nigeria.py         # cities + industry taxonomy
  collector.py       # Overpass/Places collection + enrichment
  commands/
    __init__.py      # central COMMANDS registry
    common.py        # shared helpers/menus
    info.py          # /start /menu /help
    system.py        # /owner /migrate /status /stats /offer
    find.py          # /find /search
    packs.py         # /packs
    campaign.py      # /campaign /campaigns
    pipeline.py      # /pipeline /stages /stage /leads
    intel.py         # /intel
    export.py        # /export
    callbacks.py     # button + error + fallback handlers
```
