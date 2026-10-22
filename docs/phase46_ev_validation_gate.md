# GRIDIRON EV Validation Gate — Phase 46 specification

Status: specification only; not a deployed probability model.

## Non-negotiable rules
1. Freeze all historical pregame forecasts and preserve original timestamps. Never train on the same game being evaluated.
2. All odds observations require player_id, season, week, market, direction, line, american_odds, quoted_at_utc, kickoff_utc, sportsbook. Reject quoted_at_utc >= kickoff_utc and stale prices.
3. Grade only explicitly finalized official bets as bets; candidates, leans, and conditional plays are separate.
4. For each player market, model opportunity (routes/targets/carries/attempts) and conditional efficiency, then calculate P(over), P(under), pushes, and quantiles.
5. Compare against a no-vig market-only baseline. Fit shrinkage/calibration only on earlier chronological training folds; test on untouched future folds.
6. Report Brier score, log loss, reliability by probability bin, sample size, closing line value, realized ROI, maximum drawdown, and anchor regret by market and confidence band. Use bootstrap uncertainty intervals grouped by game/week.
7. Formula: for no-push American odds a, decimal d=1+a/100 if a>0 else 1+100/abs(a); EV per $1 = P(win)*(d-1)-P(loss). With pushes P(win)+P(loss) < 1; push contributes zero.
8. Approval gate: require a verified current quote, calibrated out-of-sample probability, positive lower-confidence-bound estimated EV under predeclared uncertainty method, no unresolved injury/role alerts, and adequate historical sample. Otherwise PASS/RESEARCH only. Do not set an arbitrary 5% threshold as proof.
9. Parlay approvals require book-accepted legs, exact combined price, and estimated joint P using game-state dependence; never multiply marginal probabilities without testing independence.
10. Track each decision's model version, data version, quoted odds, implied probability, model probability, confidence interval, expected ROI, stake, and outcome.

## Immediate build sequence
A. Audit existing pipeline schemas, source availability and current tests; preserve existing snapshots.
B. Implement validated odds ingestion and pre-kickoff joins, with rejection tests.
C. Implement market baseline and rolling-origin out-of-sample calibration; compare opportunity models to baseline.
D. Add decision gate and transparent dashboard showing inputs -> P -> price -> EV -> decision.
E. Shadow-track prospective picks before permitting official +EV claims.

## Acceptance criteria
- No candidate with missing prices, unvalidated probabilities, post-kickoff information or missing joint probability can be marked approved.
- Historical metrics and bankroll results reproducible from immutable data.
- Unit tests include -110 odds, +150 odds, push handling, stale odds, leakage prevention, and correlated parlays.
- Zero approved wagers is an acceptable outcome.
