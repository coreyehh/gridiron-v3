# GRIDIRON Phase 30 — Champion vs challenger model tournament

## Purpose
Seven prior phases have produced working NFLverse model components, but many improvements are tiny and player sample definitions differ. Phase 30 **recomputes** and compares **Phase20, Phase23, Phase27, Phase28, and Phase29** on one identical Phase23-eligible player-game cohort, split by completed 2026 regular-season week.

This is the **player** receiving forecast tournament. Phase22 is a *team-volume* challenger and has to be compared separately on the same team-game cohort. Phase24 probability calibration and Phase25 sportsbook validation are also separate objectives. No direct comparisons of their scores with receiving-yard MAE.

### Methods

- For each completed target week, only **strictly previous scored weeks** enter team, player, opponent positional targeting, snap and density features; 2025 used as a historical prior.
- One Phase20 pass-attempt volume forecast supplies all five player models, isolating player-allocation changes from team-volume differences. Phase27, 28 and 29 are independent bounded adjustment candidates applied on Phase23 point forecasts, not stacked.
- Retain only player IDs forecast by both Phase20 and Phase23 to match the cohort in the 27–29 research studies; never claim this also compares Phase23's omitted-player performance.
- Pair targets, receptions and receiving yards MAE on the same player-games, show within-box-entry MAE and differences by completed week.
- Missing current-week statistical row graded zero for retrospective evaluation, but never equated to inactive.
- PFR snaps use the same **non-authoritative** unique name/team crosswalk as Phase28, including its limitations.
- Fixed, conservative research gate: >=6 completed weeks, >=1500 player-games, >=1% reduction in each of targets/catches/yards MAE, and win at least 60% of evaluated weeks on receiving-yard MAE. Do **not** promote automatically even if this gate passes; require independent prospective evaluation.

### Run the workflow

[Phase 30 in GitHub Actions](https://github.com/coreyehh/gridiron-v3/actions/workflows/phase30-model-leaderboard.yml)

Select branch `main`, leave real data **checked**, first_week `4`, last_week `18` then click Run workflow. It will skip unfinished weeks. Read the job summary for the objective rank table; a plaintext aggregated JSON artifact is produced, not a licensed sportsbook feed. No Terminal, encrypted keys or bookmaker credits.

### Caveats
Only a small number of weeks are complete in October 2026. Backtested weekly rows share participants and game environments; weeks are not independent player observations. Historical league data may be uploaded after kickoff; independent source-publishing-time attestation is not yet implemented. Data provenance, valid future forecast snapshots, official injuries/actives, actual routes, bookmaker line-specific probability calibration and sportsbook ROI remain separate gates.

**Current main champion:** Phase23 player allocation with Phase20 team volume. **Official bets: 0.** This phase is an audit and governance improvement, not a prediction profitability claim.
