# GRIDIRON Phase 34 — Auditable pregame research decision dashboard

Phase 34 produces a polished standalone **HTML dashboard** plus Markdown and JSON from the **immutable Phase31 Week 6 snapshot**. It does **not** regenerate predictions or touch live player bookmaker offers.

## Run

[Phase34 GitHub Actions workflow](https://github.com/coreyehh/gridiron-v3/actions/workflows/phase34-decision-dashboard.yml). Select `main`, leave `include_real_position_history=true`, and click **Run workflow**. All previous tests run first, then the GitHub job displays counts and uploads an artifact called `phase34-frozen-matchup-decision-dashboard`. Download the ZIP from the run's Artifacts section and open `decision_dashboard.html` in a browser. The Markdown report is in the same ZIP.

No Terminal, odds API credits, encryption keys or external dashboards are required. The HTML is standalone and has no network dependencies.

## How to interpret the board

- Shows all 13 frozen Week6 fixture projections from Phase31, sorted by projected receiving yards within a game, with targets and receptions alongside.
- Where opted in, verifies previous-week NFLverse position metadata and **filters offensive linemen / non-skill rows**. Missing position is marked `UNVERIFIED`, *not* treated as confirmed WR/TE/RB.
- Per-player status is `RESEARCH_ONLY`. It explicitly lacks game-day active verification, route assignments, opponent coverage/weather updates, player-specific sportsbook line quotes, and prospective validated probabilities at actual sportsbook thresholds.
- **No moneyline, EV, expected ROI, recommended wager, parlay, or qualified play is produced.** Neither a high projection nor historical market gap is permission to bet.
- Phase32's live odds check deliberately published aggregate quote coverage only. There is no durable, private player+book+line comparison archive available for this public dashboard.
- Phase33's historical one-week calibration assessment is insufficient to validate book-line player probabilities. Boolean evidence fields supplied by outside callers cannot promote entries.
- Every forecast is checked against the immutable snapshot payload SHA256, and the dashboard has no mechanism to overwrite forecasts after the fact.
- User-input / player names are escaped in static HTML to prevent embedded markup/scripts.
- This is a **research-facing decision dashboard**, not a full operational betting system.

## Next blockers

To provide an actual validated betting card, implement a secure player-level (not public) quote context with source timestamps, independently validate conditional market-threshold probabilities, and obtain authoritative official game-day player status, with recorded provenance and cutoff before kickoff. Retain the prospective record and do not present a model/line difference as measured profit.

Model champion: Phase23 player role + Phase20 passing volume. Official qualified bets: **0**.
