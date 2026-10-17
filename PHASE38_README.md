# GRIDIRON Phase 38 — NFL official-source probe and strict probability evaluation

This phase implements two genuine evidence tasks: an authenticated HTTPS fetch of the **official NFL.com inactives landing page** and a real-data chronological evaluation of the Phase23/24/33 research model against preselected reception/receiving-yard thresholds.

## Run

[Phase38 GitHub Actions](https://github.com/coreyehh/gridiron-v3/actions/workflows/phase38-official-calibration.yml)

Run on `main` with `run_real_history=true` and `probe_official_nfl=true` (defaults), bankroll $1000 and 1% unit. The official page and nflverse history retrieval are free; **this workflow does not call the Odds API**. Download its aggregate JSON audit and inspect the job summary.

## The NFL status distinction

- `https://www.nfl.com/inactives/` is the NFL's official inactives landing page. The HTTPS retrieval verifies the requested host, TLS and bytes, records a SHA-256 content digest and response time, handles 403 / 429 / unavailable requests gracefully.
- **This is NOT yet a player-level authenticated game-day inactives integration.** The public landing page can be empty before the inactive list is published; an HTML byte hash and a page containing a player name do not prove any specific GSIS player is active or inactive for a specific fixture.
- Player-level availability stays UNKNOWN and **official_active_status_verified=false** until a real, timestamped, fixture-bound, independently parsed official NFL or team report and identity verification is added. Absence from an unavailable inactives page does not establish ACTIVE.
- NFL football operations describes inactive-list exchange at approximately 90 minutes before kickoff: https://operations.nfl.com/gameday/pre-game/countdown-to-kickoff
- nflverse in-season rosters do **not** verify game-day active lists; FTN participation data from 2023 onward is not updated during the season.

## Actual statistical validation

- Runs prior-week-only residual training over completed 2026 weeks (using real 2025–2026 nflverse history and schedules), with missing box rows excluded as UNKNOWN rather than assigned zero.
- Explicitly distinguishes **threshold predictions** (many correlated values for a player) from **independently scored future weeks**. In Phase33 the audit yielded 1290 threshold outcomes in just one independently scored week; more numeric predictions cannot substitute for future weeks.
- Adds a schema for prospective, frozen offered FanDuel line/outcome observations with pre-kickoff timestamps. These require **private authenticated raw provider evidence**, not caller-supplied `source_authenticated=true`, and must eventually pass calibrated out-of-sample scoring.
- A Brier score on manually submitted lines is a diagnostic, not proof of calibration or sportsbook EV. No actual archived player-level FanDuel offers are accessible to the current public repo.
- Official single bets and 2–5-leg parlays remain unqualified and receive zero units. This does not mean the model makes zero predictions; it means the betting evidence gate has not passed.

## What a future official bet still requires

Authentic source-bound player status and up-to-date role/route information, privately retained legal FanDuel individual offer records, prospectively validated probabilities at exactly those offered thresholds, bookmaker combined SGP prices/acceptance, and an objectively checked matchup variance layer. No hypothetical prices, fabricated probabilities, or automatic placing wagers.
