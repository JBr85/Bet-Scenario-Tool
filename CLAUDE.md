# Bet Scenario Tool — Project Reference

## What it is
A local Flask web app for tracking, analysing, and placing bets via Betfair Exchange.
Runs at http://localhost:5000. Start with `start_bet_tool.bat` or `python app.py`.

## Tech stack
- **Backend**: Flask (Python), SQLite (`bets.db`)
- **Frontend**: Bootstrap 5, vanilla JS, Chart.js, SheetJS (xlsx export)
- **Betfair**: `betfairlightweight` v2.23.2 SDK, credentials in `betfair_config.json` (encrypted)

## Key files
| File | Role |
|------|------|
| `app.py` | All Flask routes, DB helpers, league/sport detection |
| `betfair_service.py` | Betfair API wrapper (auth, sync, market search, bet placement) |
| `bets.db` | SQLite database — single `bets` table |
| `templates/` | Jinja2 HTML pages |
| `picks/` | Folder for daily CSV picks files (configurable in Settings) |
| `betfair_config.json` | Encrypted Betfair credentials (do not commit) |

## Pages
| Route | Template | Purpose |
|-------|----------|---------|
| `/` | `index.html` | Dashboard — P&L summary, charts |
| `/data` | `data.html` | Raw bet table, upload CSV/PDF, bulk league edit, Excel export |
| `/analysis` | `analysis.html` | Scenario analysis with filters |
| `/horses` | `horses.html` | Horse racing analysis — Win/Place system tabs |
| `/today` | `today.html` | Today's bets — settled + live pending; Refresh from Betfair button |
| `/place-bets` | `place_bets.html` | Daily Picks loader + search Betfair + place live bets |
| `/settings` | `settings.html` | Staking defaults, Betfair credentials, picks folder path |

## Database schema (`bets` table)
```
id, date, match, bet_type, market, stake, matched, status, pnl,
country, league, source, odds, sport, bet_category, created_at
```
- `sport`: `'Football'` or `'Horse Racing'`
- `bet_category`: `'Win'` / `'Place'` / `'EW'` / NULL — used to separate HR systems
- `source`: `'csv'` / `'pdf'` / `'betfair'`
- `market`: usually `'Exchange'` for Betfair records

## Horse racing classification rules
- **Sport detection**: `match` field starting with `HH:MM` → Horse Racing (highest priority)
- **Bet category (Betfair sync)**: determined from `item_description.market_desc`:
  - `"To Be Placed"` in market_desc → `bet_category = 'Place'`
  - Any race description (e.g. `"1m Hcap"`) → `bet_category = 'Win'`
  - This is more reliable than the MARKET_DESCRIPTION catalogue projection (which silently fails)
- **Bet category (legacy/CSV)**: stake £1 → Win system; stake £2 → Place system
- Track/country from `HORSE_RACING_TRACK_COUNTRY` dict in `app.py`

## Football league detection
4-tier cascade in `auto_detect_league_smart()`:
1. `TEAM_MAP` (team name → country/league)
2. `BETFAIR_COMPETITION_MAP` (Betfair competition name)
3. Fuzzy team matching
4. TheSportsDB API fallback

## Betfair integration
- Login: `betfairlightweight` `login_interactive()` with username/password
- Credentials saved to `betfair_config.json` (encrypted); Settings page has a **"Connect (username)"** quick-connect button that uses saved credentials without re-entry (autocomplete disabled to prevent browser overwriting the username field)
- Sync history: `POST /api/betfair/sync` → populates `bets` table (record_count=1000). Sync DOES save to DB — "Added 0 bets" just means all records already exist (duplicate check working correctly)
- **Refresh today's HR**: `POST /api/betfair/refresh-hr-today` → deletes today's HR betfair records and re-pulls fresh (use when sync is missing Win or Place bets for today)
- **Today's refresh**: `POST /api/today/refresh` → deletes today's betfair records (all sports), re-pulls settled history (days_back=2), AND fetches live pending orders; returns `{bets, pending_bets}`
- **Pending orders**: `GET /api/today/pending` → calls `list_current_orders` (not `list_cleared_orders`) to get open/unmatched bets not yet settled; uses market catalogue lookup for event/runner names; returns same dict shape as settled bets with `status='Pending'`, `pnl=0`
- Place bets: `POST /api/betfair/place-bets` — LIMIT (fixed price) or MARKET_ON_CLOSE (SP)
- Search runners: `POST /api/betfair/search-runners` — two separate WIN/PLACE catalogue calls to avoid TOO_MUCH_DATA
- Re-classify: `POST /api/betfair/reenrich-from-betfair` → updates country/league for existing records

## Daily Picks workflow (Place Bets page)
1. Drop a CSV file into `./picks/` (configurable path in Settings)
2. CSV columns (case-insensitive): `Date` (YYMMDD), `Time` (HHMM), `Course`, `Horse`, optionally `Rank`, `ML_Prob`
3. Press **Load Picks** → table appears with checkboxes; set **Win stake £** and **Place stake £**
4. **Add Selected — Win + Place** → injects two rows per horse into the Selections table
5. **Validate All** → searches Betfair for each horse/race
6. **Place Bets** → places WIN and PLACE orders in a single action

## Daily Picks API routes
- `GET /api/picks/files` → lists CSV files in the picks folder
- `GET /api/picks/load?file=<name>` → parses a picks CSV; returns `{picks, file, message}`
  - Auto-selects today's file (YYMMDD in filename) or falls back to most recent

## Data page features
- Filter bar: text search, source filter, sport filter
- **Export to Excel** button → exports all currently visible (filtered) rows as `.xlsx` via SheetJS

## Current database state (as of May 2026)
- ~560+ total bets
- Horse racing: Win system bets (cat='Win') + Place system bets (cat='Place') from Betfair sync
- Football: includes England PL/Championship, Spain, Germany, Italy, Portugal, Turkey, France Ligue 1 & 2, European competitions, Copa, Liga DIMAYOR (Colombia)

## Today's Bets page (`/today`)
- Loads settled bets from DB on page render; JS then silently calls `/api/today/pending` to fetch live open bets and merges them in
- Pending bets are NOT stored in DB — fetched live from Betfair each time, displayed only
- Status classification (JS): `status='Settled'` → infer Won/Lost/Void from pnl sign; `status='Won'/'Lost'` direct; anything else → Pending
- Row colours: yellow tint = Pending, green = Won, red = Lost
- Summary cards count Pending/Won/Lost; P&L excludes pending (pnl=0 for those)
- Refresh button: `POST /api/today/refresh` — one call gets both settled and pending, table updates in-place

## Important implementation notes
- `record_count=1000` in `list_cleared_orders` — was 100 which caused missed bets when 30-day window exceeded 100 records
- Betfair `MARKET_DESCRIPTION` projection causes `TOO_MUCH_DATA` on broad searches — use two separate calls (WIN then PLACE) and tag with `_queried_market_type`
- `buildChoiceHtml` was removed from `place_bets.html` — don't re-add it
- Horse racing records from Betfair sync have horse name in `bet_type` and race in `match`
- Tombstone table (`deleted_bets`) prevents re-import of user-deleted records
- `refresh-hr-today` bypasses tombstones by doing a raw DELETE (not via the UI delete path) — safe because it's a deliberate full refresh, not a user deletion
- `db_insert_bet` backfills `bet_category` on duplicate betfair records if existing row has NULL category
- `betfairlightweight` v2.23.2: response attribute is `place_instruction_reports` (not `instruction_reports`)
- `reenrich_leagues(force_all=True)` runs at every startup — skips updating a record only if new classification is `Other` AND current is non-Other/Unknown
- `bf_competition` is NULL for records imported before the reenrich feature; use "Re-classify from Betfair" in Settings to back-fill
- Colombian football = **Liga DIMAYOR**; Austrian/Dutch clubs in TEAM_MAP
