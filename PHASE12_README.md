# GRIDIRON 3.0 — Phase 12: Identity and probability foundations

## Deliverables
- `scripts/phase12.py`: strict current-season player ID lookup **function**, conservative player name normalization, and leakage-separated probability diagnostic.
- `test_phase12.py`: checks that names, teams, seasons and ambiguous IDs do not silently cross-match.
- `.github/workflows/phase12-validation.yml`: manual GitHub test + fresh 2021–25 NFLverse weekly stats retrieval + empirical probability diagnostic on 2025; consumes **zero The Odds API credits**.

## Identity: no fabricated 2026 match
Matching requires a supplied roster record with **exact normalized name, exact team and same season**, producing exactly one player_id. A unique match is labeled `IDENTITY_MATCHED_NOT_ACTIVE_VERIFIED`, never active-confirmed. Ambiguous names, season mismatches, missing teams and no roster records fail closed. The repository currently has no verified 2026 roster crosswalk, and the Phase 11 event quote schema doesn't carry a trusted individual player ID. This function is **not yet wired to automatically certify real sportsbook rows**. That requires a trustworthy roster data source, an event/team reconciliation layer, and kickoff-time eligibility evidence.

## Probability: measured diagnostic, not betting-grade calibration
For each position/market included in the historical baseline:
- 2021–23: fit Ridge point forecast using strictly lagged prior-game features; fixed alpha=10.
- 2024: collect residuals from never-in-training validation season.
- 2025: hold out observed outcomes and evaluate empirical tail rates at predeclared **synthetic** thresholds.
- Score Brier loss versus a 2024 reference-frequency predictor, and show predicted/observed rates.

**Critical limitations:** The evaluated player rows are derived from observed postgame player-week data, not a verified universe of players offered by sportsbooks before kickoff; the thresholds are not real posted lines; point forecasts and probability tails aren't yet independently validated on line-specific market prices. We cannot infer true edge, +EV or portfolio ROI.

The report sets `betting_probability_approved=false`, `roi_verified=false`; any sportsbook quote remains `INSUFFICIENT_DATA`.

## Executing
1. GitHub → Actions → **GRIDIRON Phase 12 identity and probability validation** → Run workflow on `main`.
2. Check the workflow summary and download the `phase12-historical-diagnostic` artifact (14-day retention). It contains aggregate diagnostic scores, **not** licensed sportsbook quotes or secrets.
3. Phase 11 private market collection stays manual and unchanged. Phase 12 never makes The Odds API calls.

## Next measured gates
- Acquire verified event-specific 2026 roster player-ID evidence (name/team/season and identity provenance), pregame depth and active status.
- Join matched players to actual market offers at a captured timestamp.
- Evaluate held-out Brier score, log loss, probability reliability by market and probability bands on true offered-line cohorts.
- Record a pre-kickoff immutable pick board; confirm bookmaker settlement rules and historical outcomes before any ROI claim.
