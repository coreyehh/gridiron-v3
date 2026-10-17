# GRIDIRON Phase35 — FanDuel-only betting and portfolio framework

This is **NOT a list of recommended or qualified real bets yet**. It adds the missing decision layer and bankroll architecture for eventual FanDuel singles and 2–5-leg parlays, but the validated real-line probabilities, official gameday actives, route-role checks, individual offer archival, and FanDuel accepted combined parlay quotes are not present. Thus **zero picks qualify**, and no stake is assigned to unqualified candidates.

## How to run

[GitHub Actions: Phase35](https://github.com/coreyehh/gridiron-v3/actions/workflows/phase35-fanduel-portfolio.yml)

Run on `main`, default bankroll $1,000, 1% per unit ($10). Leave `request_live_fanduel=false` for FREE model/unit tests. The generated artifact contains an aggregate portfolio summary and an accountable SHA256-locked, zero-bet ledger.

For ONE upcoming frozen Week6 game only, check `request_live_fanduel=true` to opt into an Odds API call requesting **FanDuel-only** `player_receptions` and `player_reception_yds` markets. The workflow uses the existing `ODDS_API_KEY` secret; it may consume credits. It never requests other bookmakers, does not log player-specific FanDuel prices, does not export a bet slip, and does not pretend FanDuel joint parlay quotes are supplied by the API.

## Staking policy

- User-editable bankroll with **1u = 1%** of bankroll by default (allowed 0.5%, 1%, 2%).
- **Max single 1u**, minimum quoted EV threshold 3% for eligibility *only after independent probability validation*, quarter-Kelly with cap to assign singles, total slate exposure **max 3u**, preliminary parlay caps: 2 legs 0.5u; 3 legs 0.4u; 4 legs 0.25u; 5 legs 0.1u.
- No bet if it fails identity, event/market pairing, time-based quote validity, pregame forecast lock, independently verified official status, role/route, matchup evidence, or real-line probability calibration.
- An unvalidated game-day boolean is not accepted as official. Prices alone are never evidence of +EV. Outcome-first/price-second ranking only among qualified bets.
- Same-game or cross-game parlays require **independently modeled joint probability** and an actual accepted **FanDuel combined price**. Multiplying singles' prices or independent probabilities is NOT an approved substitute. No unqualified legs, contradictory duplicate player markets, or unverified book acceptance.
- This architecture does not yet construct or rank actual eligible parlays because evidence inputs are missing.
- No wagers are auto-placed. Results and ROI are not fabricated: ledger records zero official bets and no realized ROI until auditable bets and their results are integrated.

## Critical follow-up work

1. Verified, timestamped official player game-day active source (with provenance) and role/route checks.
2. Private per-player authenticated FanDuel quote storage with expiry and user-controlled access; no licensed quotes in public repo.
3. Sufficient truly prospective calibrated probability evidence at specific offered FanDuel thresholds; correct systematic player availability selection bias.
4. Joint outcome model for correlated parlay legs, actual FanDuel parlay payouts/acceptance and whole-portfolio correlation limits.
5. Immutable snapshots of picks as made, settlements/closing lines and ROI on real recorded stakes.

Phase35 delivers the runnable, safe portfolio foundation and eligibility gates. It does **not** certify betting profitability or imply matches against private FanDuel quotes can be exported publicly.
