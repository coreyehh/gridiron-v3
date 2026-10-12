# GRIDIRON — Free The Odds API test (before paid history)

## What it verifies
- NFL event discovery (provider documents this as zero-credit).
- With an *explicitly enabled* switch, ONE upcoming game's two markets: `player_receptions` and `player_reception_yds`.
- Which books returned those markets, how many outcome rows, and provider-reported usage credits.
- It does **NOT** claim Bet365 coverage, historical odds, profitability, calibrated hit probabilities, or betting edges.

## How to run
1. Sign up for The Odds API's **Starter / Free** plan at https://the-odds-api.com.
2. Copy your key **directly into GitHub**, not into a chat, public repo or source file.
3. Repository → Settings → Secrets and variables → Actions → New repository secret.
4. Name exactly `ODDS_API_KEY` and paste the key. Save it. Do not add it to `.env` committed files.
5. Open Actions → **GRIDIRON free odds coverage check** → **Run workflow**.
6. First run: **test_player_props = false**, region `us`. Checks available NFL events for no credit charge.
7. Second run, if events are present: **test_player_props = true**, region `us`. This makes exactly one paid-credit event odds request (the free subscription still has a credit balance). You can instead choose `ca` or `us2`.
8. The run's short-lived artifact `gridiron-free-odds-smoke` contains only aggregated bookstore/market coverage and credit headers—no player odds or API key. Send the workflow-run URL for a coverage interpretation.

## Provider source and constraints
- https://the-odds-api.com/liveapi/guides/v4/
- https://the-odds-api.com/sports-odds-data/bookmaker-apis.html
- https://the-odds-api.com/sports-odds-data/betting-markets.html

US provider keys include `draftkings`, `fanduel`, `betmgm` and `betrivers`; availability per event can differ. Bet365 is **not** listed as an NFL US/CA book in the linked documentation, so a working key does not guarantee bet365 lines. Other sportsbooks in region `us2` and Canada can be tested in a separate user-initiated run.

GET /v4/sports/{sport}/events is quota-free according to docs. GET single-event odds has a cost based on returned market count and regions. This pilot requests two prop markets and one region, and logs x-requests-last / used / remaining. Data may be unavailable for some dates/books/markets.

## Safeguards and honest limits
- No runs on a recurring schedule, no sportsbook wagers, no order submission, no automatic purchases.
- The snapshot file is a transient 7-day GitHub Actions artifact, not a historical licensed archive or a real-time always-on dashboard. We can add controlled pregame-only snapshot capture later, after checking data-retention terms.
- If no key is set, job fails with an instruction, not a raw HTTP URL or the key.
- This repository currently is public; do not commit keys, licensed raw odds or private wager ledgers.
- Historical ROI testing still requires archived pregame quotations from 2023 onward (or an alternative provider), independent grades, and pregame calibration.
