# GRIDIRON 3.0 — Phase 18: current-season form and pre-quote forecast lock

## What actually changed

The Phase 18 research pipeline (`scripts/phase18.py`) now:
1. Discovers one upcoming NFL event via The Odds API event listing (does not spend prop-market request credits).
2. Retrieves **fresh nflverse season-roster identities**, a 2026 nflverse game schedule and complete historical player-week stats through 2026.
3. Maps the chosen opponent pair and local game date to a **unique 2026 regular-season week** from the nflverse schedule. Late primetime kickoffs can appear one date later in UTC.
4. Restricts **2026 player form** to earlier regular-season weeks for which the schedule reports completed scores for *all* games in that week. The selected event's own week, incomplete weeks, and later weeks are excluded. Uses the last 3/5 **observed games** for each player; this is not equivalent to recent snap/route share.
5. Fits the same simple RB/WR/TE Ridge baseline on 2021–2025 only. Uses eligible players' latest 2026 form when available to generate receptions and receiving-yard **point forecasts for all matching roster players** before the paid odds request.
6. Serializes the complete player-level prediction snapshot into runner-local ignored `private_data/phase18_locked_forecasts.json`, hashes the file with SHA-256 and timestamps the lock **before calling the paid sportsbook event odds endpoint**.
7. Queries one upcoming game's authentic player-prop lines; joins only player IDs matched uniquely to the opposing teams. Excludes odds whose **bookmaker quote update timestamp predates the lock**, even when the response itself was captured after the lock.
8. Uploads only anonymous coverage counts, per-market line-gap statistics, the model/data fingerprint, cutoff weeks and provider quota. **Never uploads player-level forecasts, raw licensed quotations or credentials**.

## Important evidence limitations

- **This is now a real pre-query freeze**, but the lock lives only on an ephemeral GitHub runner. Phase 18 *does not durably preserve an independent archive of player-level pregame picks*. SHA-256 alone is not sufficient for independently verifying future pick claims.
- The nflverse CSV stats and schedule are downloaded at run time; the code records source hashes, but does not establish the exact original publication times of individual games or historical source revisions. It filters for completed earlier weeks and cannot certify point-in-time accuracy of a previously run forecast.
- **No official active/inactive verification.** A player on a current roster may not be available for the game. Game-day active status still requires authoritative reports.
- **No opponent-specific scheme, coverage, pace, player participation, OL, weather or injury inputs.** Phase 18 is a current-form point forecast probe, **not yet a complete GRIDIRON matchup model**.
- Historical model fitting still has documented postgame-cohort selection bias. Nothing here establishes edge versus actual sportsbook lines.
- It does not compute an approved distribution / probability at the quoted line, push probability, price-adjusted expected ROI, or official picks. Every market remains **INSUFFICIENT_DATA**; `bets_qualified=0`.
- A game with an unreconciled schedule (e.g. postponed game or unexpected team abbreviation) intentionally **fails closed**. A bookmaker quote last updated before the lock is counted but not compared. This may mean **zero comparable rows** in an otherwise successful live run.
- Only regular-season games supported; failures or unavailable 2026 stats are reported rather than silently falling back to 2025.

## Running Phase 18

Open GitHub Actions → **GRIDIRON Phase 18 current form and prequote lock** → Run workflow (`main`).

First leave `use_api_credits` **unchecked** to execute the Phase 18 + Phase 17 fixture tests without accessing the live data feeds or using any sportsbook credits.

If it passes, rerun with `use_api_credits` **checked**, region `us`, and a valid encrypted `ODDS_API_KEY`. The live run downloads nflverse data, forms and locks predictions, then requests the one chosen event's two prop markets. Only aggregate `phase18-prequote-lock-audit` JSON is uploaded; credits spent and remaining are reported by the provider.

### Next required layers

Ingest and time-stamp authoritative weekly NFL injury/inactive reports, opponent and OL context, actual routes and volume inputs, independently calibrated real-offered-line probability models, and a protected **durable** snapshot + prospective result ledger before asserting any betting ROI.
