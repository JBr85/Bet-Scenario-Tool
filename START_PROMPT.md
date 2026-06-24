# Start Prompt — Bet Scenario Tool

Paste this at the start of a new Claude session to get full context quickly.

---

I'm working on my **Bet Scenario Tool** — a local Flask/SQLite web app at:
`c:\Users\james\OneDrive\Documents\Bet Scenario Tool`

Read `CLAUDE.md` in that folder for the full technical reference before doing anything.

## Quick orientation

- **Backend**: `app.py` (all routes + DB helpers), `betfair_service.py` (Betfair API)
- **DB**: `bets.db` — one `bets` table; key fields: `sport`, `bet_category` (Win/Place), `source` (betfair/csv/pdf)
- **Start app**: `start_bet_tool.bat` or `python app.py` → http://localhost:5000
- **Auto-reload**: launcher now uses `python.exe` (with console window) so Flask's debug reloader actually restarts on `app.py` edits — don't close the small console window

## What was built in the last session (14 May 2026)

### Daily Breakdown on Horse Racing page
- New sortable table above the bets list on `/horses`, mirrors the Analysis page style
- Columns: Date, Bets, Won, Lost, Staked, Win P&L, Place P&L, P&L, End Bank
- Respects the active System filter (All / Win / Place / EW) and date range
- Backend: `/api/horses/analysis` now returns `daily_results` aggregated from `bets_out`
- Frontend: new `renderDaily()` / `sortDaily()` in `templates/horses.html`

### Launcher reload fix
- `start_bet_tool.bat` switched from `pythonw.exe` (windowless) → `python.exe` (console)
- Reason: under `pythonw` Flask's reloader detected file changes but the subprocess restart silently failed because there was no console handle — required manual restart
- Trade-off: a console window now appears (titled "Bet Scenario Tool"). Minimize it, don't close it.

## Known watch-outs

- Betfair `MARKET_DESCRIPTION` projection causes `TOO_MUCH_DATA` on broad searches — search_runners uses two separate WIN/PLACE calls tagged with `_queried_market_type`
- `buildChoiceHtml` was removed from `place_bets.html` — don't re-add it
- Horse racing sync: horse name → `bet_type`, race event → `match`
- HR `bet_category` is determined from `item_description.market_desc` ("To Be Placed" → Place, else Win) — more reliable than the catalogue projection
- Tombstone table (`deleted_bets`) blocks re-import of user-deleted records; `refresh-hr-today` bypasses this intentionally via raw DELETE
- `betfairlightweight` v2.23.2: response attribute is `place_instruction_reports`
- `reenrich_leagues(force_all=True)` runs at every startup
- Project lives in OneDrive — occasional spurious reloads possible if OneDrive touches files; can narrow reloader watch list if it becomes annoying

## Things that may need attention

- Some older HR bets may still have `bet_category = NULL` if imported before the sync fix — use "Refresh Today's HR" in Settings to fix today's, or "Re-classify from Betfair" for backfill
- The Horses page splits by `bet_category` (Win/Place tabs) — any NULL records won't appear in either tab
