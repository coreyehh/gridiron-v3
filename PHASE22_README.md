# GRIDIRON Phase 22 — game-script challenger and uncertainty audit

## Scope
Phase 21 showed Phase 20 beats a 3-game-average baseline for overall team pass/rush attempts and player receiving outcomes, but struggled in blowouts. **Do not claim an actual game-state simulation yet.**

Phase 22 adds a deliberately limited, auditable challenger:
- Pre-game strength proxy: each team's last four completed 2026 game *final-score margins* relative to the opponent; buckets `favored`, `close`, `underdog` by 8-point average margin differential. **No future or current-game final scores can be features.**
- Phase 20 remains the base team pass/rush attempt projection.
- Candidate correction: prior weeks' signed Phase 20 forecasting residuals from the same pregame strength bucket, minimum 12 observations, shrunk by `n/(n+24)`, max 5 attempts adjustment. **Prior completed weeks only; current week errors are appended AFTER every matchup in that week is predicted.**
- Preliminary 80% team-attempt intervals: a historical absolute-residual quantile, requiring at least 30 *earlier* matching-metric errors before issuing a range. The interval coverage is measured on subsequent completed games.
- Direct head-to-head MAE and interval coverage checks for team pass and rush attempts. The current Phase 20 production engine **cannot be replaced** unless *both* attempt categories improve and each has at least 30 interval checks with observed coverage in [72%, 88%]. This gate is conservative but heuristic, not statistical proof.
- No player target/route/active-status model additions yet. A later phase will add route participation and target-share stability from authenticated prior-game participation feeds and measure their individual effect.
- No simulated in-game lead probabilities, probability that a player clears an actual sportsbook line, betting EV or claimed profitable plays.

## Run
[Run Phase 22 in GitHub Actions](https://github.com/coreyehh/gridiron-v3/actions/workflows/phase22-script-audit.yml)
- Branch `main`
- `run_real_data`: **checked**
- `first_week`: `2`
- `last_week`: `18` (only fully completed 2026 regular-season weeks are included)

No odds credits, encryption key or installed local dashboard. Results print in the GitHub job summary; in the chat, the assistant should retrieve the summary, compare Phase 20 and Phase 22 and explicitly state whether the model qualifies for promotion.

## Known limitations
- This is a retrospective walk-forward benchmark on 2026 files downloaded after games. Publication timing and selection of Phase 22 heuristics were not preregistered.
- Last-four-game final-score margin is **not** in-game script, Vegas expected spread, or an independently priced outcome distribution.
- Because calibration has few weeks, 80% prediction ranges have low sample counts and may not achieve nominal coverage. True 80% coverage is not guaranteed.
- Intervals are symmetric count deviations around team attempt forecasts, not full joint team/player distributions.
- A valid player prop system needs independently verified day-of actives, OL/coverage/route usage, book offer timestamps, and calibrated conditional player-market probabilities. None of those are present here.
