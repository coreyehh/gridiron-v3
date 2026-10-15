# GRIDIRON 3.0 — Phase 20: forecast team opportunity BEFORE individual props

## Why this phase

Bills–Rams finished 37–34 in overtime, but Buffalo attempted only 19 passes while the Rams attempted 54. A model that treats 71 points as automatic OVER receptions on both sides is fundamentally mis-specified.

Phase 20 adds a **separate pass-attempt and rush-attempt volume baseline for each offense**, then derives player targets, catches and yards from within-team opportunity. The 2026 current-season sample is shrunk toward 2025 and a small weight is assigned to the opponent's recently observed pass/rush attempts faced. The formulas are intentionally simple and **NOT yet backtested**. A high projected score never automatically increases passing attempts.

### Volume model

- Use only nflverse **regular-season player-week data** for 2025 and 2026.
- Require target game to be a unique scheduled 2026 regular-season fixture for the input teams and week.
- 2026 form may include only **fully completed previous weeks**, determined from nflverse schedule game scores. Data from the target week or later are excluded, even if present in a newly downloaded file.
- Sum NFLverse QB/all-player passing attempts and rushing carries per team per completed game. Use 2025 recent team baseline with current-season empirical Bayes shrinkage `n/(n+4)`.
- Blend at most **25%** of opponent recent attempts faced; shrink further when little data. No points or betting total features.
- Player targets per projected pass attempt = player's observed 2026 targets / team's complete-window actual pass attempts; use conditional catch rate and yards-per-target with lightweight prior-season 2025 same-team rates and generic smoothing. Zero-target players do not appear. The system does **not** know official game-day actives, route participation, snap shares, coverage or injury status.
- The expected outputs are *point forecasts* only, never implied calibrated win probabilities or confirmed +EV selections.

### Running, without encryption keys or paid APIs

GitHub Actions → [GRIDIRON Phase 20 opportunity and volume](https://github.com/coreyehh/gridiron-v3/actions/workflows/phase20-opportunity.yml).

**First validation:** Leave `run_real_data` **unchecked** and click Run workflow. Tests validate model invariants and incomplete-week exclusion. These are fixtures, not a real-model backtest.

**Real research run:** Set `run_real_data` **checked**, two real matchup team codes such as `SEA` and `DEN`, plus the applicable regular-season week (for Thursday October 15, **week 6**). Click Run workflow. It consumes **zero sportsbook API credits and needs no archive key**. The readable player-by-player research table is printed directly in the GitHub **job summary** and logs. Names are joined to nflverse 2026 roster identities. No odds or real sportsbook price comparisons are in Phase 20.

The GitHub workflow stores a reproducibility JSON for 30 days as `phase20-team-opportunity-report`. This is publicly accessible in a public repository to anyone with appropriate access; it includes ordinary public nflverse player stats only. **Do not store licensed, bookmaker-specific odds, usernames, secrets, or personal betting activity in this artifact.**

### Critical caveats

This phase is useful for diagnosing how many **opportunities** we expect, not for making bets. The model has not been validated on a held-out 2026 sample; projections could be biased by team changes, missing players, drops/sacks, unusual overtime, 2025-to-2026 usage shifts, and missing day-of availability. The opponent influence is heuristic, and the player denominator is actual **team passing attempts**, not route participation. If an input column or historical schedule isn't available, the model fails closed rather than inventing data.

Next work: historical walk-forward evaluation with lineup/injury/coverage sources; model target shares with route/snap certainty; account for game-state branching and interceptions/sacks; fit predictive residual distributions; calibrate P(clear) to real sportsbook lines; test price error and prospective official picks independently.

**Data output delivery requirement:** the assistant should bring the actual run results into chat and explain ranked *opportunity differences*, without asking the user to install software, unlock files, or use Terminal.
