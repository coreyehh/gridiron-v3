# GRIDIRON Phase 23 — Player role & target-share challenger

## Goal
Phase 21 showed player-level accuracy barely improved despite substantially better team passing and rushing opportunity estimates. Phase 23 challenges Phase 20's uniform five-game target share with a role-shift-sensitive model.

## Current implementation (honest data labels)
- **Authentic source:** nflverse 2025 + 2026 regular-season player-week datasets, plus season schedule.
- **Inputs available:** pregame completed-game target counts, receptions, receiving yards, team attempts, observed team/player IDs.
- **NOT AVAILABLE in this dataset:** per-route participation, snaps by personnel package, formal injury/active verification, opponent coverage shells, official market lines.
- **Role proxy:** full recent five-team-game target share blended with the most recent two-team-game share, shrunk toward older team-specific player usage according to target observation count. Model only forecasts players with observations in at least one of the last three weeks. These are heuristics to challenge, not validated usage forecasts.
- **Strict evaluation:** only 2025 and earlier completed 2026 weeks can contribute to a game's forecast; Week W outcomes grade Week W but do not enter predictions. Weekly finished-score presence gates data availability.
- **Equal player cohort:** Phase 20 and Phase 23 scored against the same Phase 20-eligible player IDs, including zero actual yards for players absent from that week's stats feed. "Absent from box score" does not mean officially ruled out. The challenger assigns zero to stale players rather than quietly omitting failures.
- **Markets:** targets, receptions and receiving yards. MAE per player-game and diagnostic splits by seen/unseen in box score and recent/stale player role.
- **Promotion gate:** all three player MAEs must improve before Phase 23 can become an internal research candidate; no profitable bet claims. Even if passed, model is *only* a retrospective challenger—not authorized to issue betting probabilities or picks.

## Run it
[GRIDIRON Phase 23 workflow](https://github.com/coreyehh/gridiron-v3/actions/workflows/phase23-role-model.yml)
- Select branch `main`.
- `run_real_data = checked`
- `first_week = 4`; `last_week = 18` (will score only complete 2026 weeks).
- Click Run workflow.
- Read the GitHub job summary, or return to ChatGPT and say `complete`; results can be read directly from logs.
- **No secret key, download, Terminal setup, encrypted artifacts, or paid odds credits.**

## Important limitations
Downloaded files are current postgame snapshots; strict week filtering does not prove contemporaneous source publication or point-in-time roster state. This is a walk-forward simulation, not preregistered prospective betting performance. Adding routes, confirmed game-day actives, defensive coverage and more reliable team-reconciliation logic requires independent source data and testing. Phase 22's pregame script challenger is not yet plugged into this player-target evaluation; Phase 23 tests player allocation changes on the existing Phase 20 team volume forecast to isolate this variable.
