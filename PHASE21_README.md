# GRIDIRON Phase 21 — Walk-forward accuracy audit

## Goal

Before adding speculative game-state parameters, establish whether Phase 20 predicts **real team passing/rushing attempts and player targets/receptions/yards** more accurately than a transparent trailing-average baseline.

## Protocol

- Download authentic 2025 and 2026 nflverse player-week stats and the full NFLverse schedule.
- Score only **fully completed** 2026 regular-season weeks. For each tested game in week W, derive every predictor strictly from 2025 and completed 2026 weeks **before W**.
- Re-run the actual Phase 20 team-opportunity engine. For each team passing/rushing volume market, compare its prediction to a **last-three 2026 games' volume average** (where fewer games exist, use available games).
- For player targets/receptions/receiving yards, compare Phase 20's forecasts against that player's totals divided by the number of prior observed team games in the **last three completed weeks** (including zero for that player if they had no row).
- Grade against actual Week W player-week outcomes, with the caveat that a projected player absent from nflverse Week W statistics is assigned zero production without claiming active/inactive status.
- Report mean absolute error (MAE) separately in attempt/count units or yards—never pool unlike units. Require same evaluation population for the model and baseline.
- Segment errors by **actual** game total (`<40`, `40–49`, `50+`) and final point margin (`17+` versus smaller). These are **postgame diagnostics only**, never pregame predictors. Includes overtime where present in actual player stats.
- Publish a directly readable, unencrypted GitHub run summary and a JSON evaluation artifact. This contains public NFLverse-based aggregates only, **no bookmaker quotes, secret keys, bets, account details or licensed odds**.
- No probability distribution, confidence, bookmaker advantage or profitable ROI is demonstrated by these point-error comparisons.

## Run

Actions → [GRIDIRON Phase 21 honest walk-forward evaluation](https://github.com/coreyehh/gridiron-v3/actions/workflows/phase21-walkforward.yml).

1. Validate tests: leave `run_real_data` **unchecked**. This tests withheld-current-week integrity, score-only-used-for-grading, no incomplete-week results, simple baseline calculation and Phase 20 fixtures. **No paid credits**.
2. Real benchmark: check `run_real_data`, set `first_week=2` and `last_week=18`. Only completed weeks will be scored. The job summary prints actual model vs baseline errors, and the JSON is archived 30 days.
3. Return to this chat and say completed; I will inspect the run logs and report exactly which markets improved, regressed, and have inadequate sample size.

## Trust and future work

These tests use nflverse files downloaded after the games, with week filtering but no independent point-in-time feed publication history. Evaluation includes unverified availability for players who later disappeared from the box score, and all Phase 20 heuristics were formulated while earlier-season results were known. This is a research walk-forward simulation, **not a preregistered prospective holdout**. It does not establish a profit edge.

Phase 21's objective is to **measure conditional residual error**, not to claim the volatility model is calibrated. After auditing Phase 20 and trailing averages, add empirically tested game-state scenario probabilities, estimated quantiles and coverage calibration, and then later a locked real-book offered-line pricing assessment.
