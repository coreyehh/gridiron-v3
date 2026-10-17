# GRIDIRON 3.0 — Phase 28: Genuine prior-game offensive snap participation

**New source:** [nflverse snap counts](https://github.com/nflverse/nflverse-data/releases/tag/snap_counts), sourced from Pro Football Reference, downloaded from `snap_counts_2026.parquet`. This is game-level **offensive snaps and offensive snap share**. It is NOT a route count, official inactive list, depth chart, or current-season availability guarantee.

**Identity limitation:** PFR reports PFR IDs, while nflverse's player-week production dataset uses GSIS IDs. Our current narrow crosswalk requires a unique normalized name + team + week, with a corroborating 2026 roster identity. Incomplete or ambiguous matches are **not assigned zero snaps** and must never be considered verified GSIS-to-PFR identification. The run measures join coverage before deciding whether to model the variable.

**Model challenger:** Fixed prior-only mean snap share (latest 2 vs trailing 5), minimum two matched past games. Apply a small bounded multiplier (about 0.91–1.09) to Phase23 player opportunity, catches, and yards, then compare identical player-games against actual completed 2026 box scores. Never use target-week snap counts to predict target-week output. Missing 2026 game-stat lines are graded zero in the existing historical evaluator but **not labeled inactive**.

## Run
[Phase 28 GitHub Action](https://github.com/coreyehh/gridiron-v3/actions/workflows/phase28-snap-participation.yml)

On branch `main`, leave `run_real_data=true`, team fields blank, week `0`, click **Run workflow**. You get a readable report in GitHub Actions and a source-hashed JSON artifact. No Terminal, odds API charges, encryption keys, or manual uploads.

## Promotion criteria

Compare MAE for targets/receptions/receiving yards on identical samples. Also inspect the denominator: how many forecast player-games have at least two prior snap records, and the sample with adequate coverage. Even if the small weeks 4–5 historical set improves, keep this as a challenger pending a larger prospective season and a **reliable PFR-to-GSIS ID mapping**.

Official game-day actives, injury status, receiving routes, OL/coverage, market-specific bookmaker probabilities, and verified sportsbook profitability remain unimplemented. Qualified bets = 0.
