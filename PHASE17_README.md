# GRIDIRON 3.0 — Phase 17: Real-player historical-only point forecast probe

## Published components
- `scripts/phase17.py` generates position-specific RB/WR/TE receptions and receiving-yard **point estimates** for uniquely matched NFL player IDs using data observed in **2021–2025**, never the future 2026 game's statistics.
- `test_phase17.py` tests the history-only guard, use of the latest historical sample, no-bet behavior and refusal to pick same-named opponents.
- `.github/workflows/phase17-validation.yml` is manually dispatched and uses **zero sportsbook credits by default**. Its optional live run fetches a new roster, downloads 2021–2025 historical nflverse stats, then requests exactly one upcoming NFL game's two live markets from The Odds API and computes anonymous projection-vs-line gap summaries.

## Crucial limitations
This is a **historical-only projection research probe**, not a verified current-game projection engine. The model is fit on past observed player-week statistics; its latest player prior is from 2025 or earlier. It currently does **not** include 2026 form, recent team personnel, injuries, game-day actives, route share, opponent coverage, coaching context, weather, or game pace. Some 2026 rookies and players with little history will be unprojectable. It does not certify historical offered-market sample representativeness. The current historical evaluation architecture still exhibits survivorship bias from postgame stat rows.

The probe uses GSIS identity matching with the same strict season/team/name/roster as-of safeguards from Phase 16. Real quotes and actual player-level point projections remain in the temporary GitHub runner's ignored `private_data/`. Uploaded artifacts and logs contain only aggregate counts and differences, not player-level lines.

**Timestamp caveat:** Projection generation takes place after the API fetch; these projections are **not** generated before the bookmaker's `quoted_at_utc` timestamp. Therefore, they are research comparisons only and **do not pass** Phase 14's strict projection-before-quote decision gate. Do not portray these as official pre-quote or immutable locked predictions. To make a true prequote ledger, produce and timestamp independent predictions **before fetching the sportsbook quote**, and compare only those later quotes. Phase 17 does not create those official picks.

No distribution tails are calibrated at real bookmaker thresholds. Differences between a historical-only estimate and a sportsbook line are **not a probability edge** or +EV. All decisions remain `INSUFFICIENT_DATA`; no bet recommendations, ROI claims or official pick snapshots.

## Run
Open GitHub Actions → **GRIDIRON Phase 17 historical pregame projection probe** → Run workflow on `main`.

- First run with `use_api_credits` **unchecked** (tests and entrypoint only).
- If successful, rerun with it **checked**, region `us`. This uses some of the 494 API credits last confirmed in Phase 16 and may change the remaining count. The exact quota is reported afterward.
- Inspect workflow logs or the `phase17-projection-coverage` artifact (14-day retention) for matched player-market combinations, number of generated projections, missing player history, and aggregate line/projection gaps.

## Next experimental gate
Ingest source-timestamped 2026 player-week form and the actual NFL matchup schedule, establish strict last-completed-game cutoff, add verified current role/active statuses and opponent context, freeze model prediction snapshots before quote collection, then independently calibrate offered-line probabilities and grade prospective bets.
