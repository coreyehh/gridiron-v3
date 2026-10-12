# Phase 8: Historical passing volume and RB receiving opportunity

This phase uses official NFLverse play-by-play release parquet files (2021–2025) and player summary statistics to test whether pregame-known opportunity indicators improve forecast accuracy for RB receptions and RB receiving yards.

## Data chain
- PBP `posteam`, `pass_attempt`, `week`, `season`: observed team passing attempts per week.
- Historical player weekly `targets`, `receptions`, `receiving_yards`, `recent_team`.
- Derived: each historical player's targets / team's pass attempts; catches / targets; receiving yards / target.
- Before **predicting** a player-week, the model uses **shifted** rolling averages of team attempts and RB target participation/efficiency plus earlier stats-only features. Tests assert that this week's targets do not enter this week's predictors.

## Evaluation
- Train: 2021–23, choose model hyperparameter using 2024 only, 2025 held out.
- Compare a stats-only Ridge model and opportunity-augmented Ridge model on the **identical 2025 RB player-week observations**.
- Primary metric MAE, diagnostic RMSE.
- Dashboard reads `docs/data/opportunity_evaluation.json` after a successful Actions run.

## Strict limitations
- Historical roster and active player universe not fully reconstructed. The source selects **postgame-observed player-weeks**, and eligibility uses only prior usage as a proxy.
- Targets/attempts is a **proxy for target share**, not RB route participation. No routes or opponent coverage inputs yet.
- Team passing opportunities are lagged previous-game attempts and not an actual future-game volume forecast with matchup/weather adjustment.
- No historical book-offered lines, no timestamped odds, no calibrated P(clear), no real bettor ROI, no certified bet plays.
- This repo is public; don't commit private betting history or licensed feeds.

## Run
GitHub → Actions → NFLverse historical data refresh → Run workflow (main).
Download run artifact for `opportunity_features.csv`. Review `docs/data/opportunity_evaluation.json` or `docs/index.html` after publishing.
