# GRIDIRON 3.0 — Phase 13: Probability calibration bias test

## Purpose
Phase 12 showed the empirical over-probability forecast frequently exceeded observed over rates in 2025. Phase 13 **tests** whether a pre-specified, pre-2025 logit-offset adjustment reduces that bias and improves probability scores. It never assumes the correction helps.

## Chronological and isolation contract
- Use lagged NFLverse player-week features from 2021–2025. The population is still drawn from **postgame** observed player records, and is NOT a sportsbook offered-markets cohort.
- Fit one Ridge point-forecast model per position/market on 2021–23 only; alpha is fixed at 10, not chosen using 2025 outcomes.
- Use 2024 Weeks 1–9 to obtain an earlier out-of-sample residual distribution.
- Choose a **single per-market logit offset** from the fixed grid [-0.4,-0.3,-0.2,-0.1,0,+0.1,+0.2] using 2024 Weeks 10+ only. A zero shift remains available; require at least a 0.00001 Brier improvement before selecting nonzero. Then shrink the chosen offset by 50% to reduce overfitting.
- For the 2025 heldout comparison, apply both baseline and corrected probabilities to the **same** full-2024 residual reference, at distinct synthetic thresholds fixed before inspecting 2025 outcomes. Thus any change in 2025 score comes only from the chosen offset.
- Report Brier, log loss, empirical calibration error across five fixed bins, predicted versus observed over rate, and sample sizes. Some metrics may deteriorate! Report those failures.
- No player IDs, roster or pregame active status magically verified. No real historic line prices, no ROI calculation, no BET selections.

## Run
Open GitHub Actions → **GRIDIRON Phase 13 probability calibration** → Run workflow on `main`. The workflow runs 6 invariant tests and downloads public NFLverse historical data. It makes **zero** Odds API requests; the resulting `phase13-calibration-diagnostic` artifact holds aggregate evaluation only. The workflow is manual, because the connected GitHub tool currently cannot dispatch Actions runs.

## Decision
Improving Brier against an uncalibrated baseline on 2025 is a **diagnostic** success, not betting authorization. Proceed to verified game-specific 2026 player-ID mapping, historical offered markets/quoted lines, prospective timestamped predictions and proper ROI audits. The report always sets `betting_probability_approved=false`, `roi_verified=false`.
