# GRIDIRON Phase 10 — historical sportsbook pricing gate

## Source findings (verified 2026-10-12)

NFLverse supplies statistics and play-by-play but **does not supply timestamped bookmaker NFL player-prop lines**. The Odds API (https://the-odds-api.com/liveapi/guides/v4/) documents historical *per-event* player-prop snapshots after 2023-05-03, available on paid plans. **This is a candidate data provider only**, not a connected account, purchased feed or proof of NFL market coverage at any specific timestamp. Confirm NFL seasons, sportsbooks, terms, retention rights and historical event market availability before purchasing. Other vendors may offer alternative archives.

## Current integration

The `scripts/odds_audit.py` importer accepts *only* a locally provided archived quote CSV at `private_data/historical_prop_quotes.csv`. The directory is ignored by Git. It is never auto-populated with invented markets and the public dashboard receives only **aggregate audit statistics**. The regular public GitHub Actions job runs in no-data mode by default because there is no licensed/verified input, and must not publicly persist vendor quotes or API keys.

Required CSV columns:
```
source_id,event_id,player_id,season,week,market,side,line,american_odds,bookmaker,quoted_at_utc,kickoff_at_utc,provider_name
```
Supported markets: `receptions,receiving_yards,rushing_yards,passing_yards,rushing_attempts,passing_attempts`. Side: `over` or `under`. Times must be explicit UTC, ending in `Z`. Quote must precede scheduled kickoff strictly. `player_id` must be the verified NFLverse player ID **from a separately checked vendor player-name mapping**, never fuzzy-name matched automatically. Line and price must come from an authentic sportsbook archival snapshot; user screenshots without a verifiable timestamp are not sufficient to certify historical value.

## Pricing formulas

- American odds -110 => break-even probability 110 / (110 + 100) = 52.381%.
- American odds +125 => break-even probability 100 / (125 + 100) = 44.444%.
- Win payout per unit risked: negative American odds = 100 / abs(odds); positive = odds / 100.
- Expected return = model's independently calibrated pregame P(win) x payout - P(loss), including exact push handling.

**Market implied probability is NOT a calibrated model win probability.**

## Next tasks before claiming value

1. Identify and approve an archival odds data source. Do not purchase/query any paid endpoint automatically.
2. Build stable event/player crosswalk and verify NFLverse outcomes plus exact market settlement; preserve market time and pregame snapshot.
3. Freeze pre-kickoff predictions without using the same game's results or future price movements; calibrate P(over/under) on historical pregame-only data.
4. Chronologically test ROI, log loss/Brier, CLV and net units **for actual eligible offers**, separately for sportsbook and over/under, including stake, pushes and missing-market exclusions. Settle against independent box score facts.
5. Backtest a declared selection policy. Report all decisions, including passes; calculate realized ROI only where authentic sportsbook prices were available at decision time.
6. Do not disclose licensed quote rows or credentials publicly; this repo is currently public, so use a private repository and GitHub encrypted secrets with minimal scopes before any vendor connection.

## Pipeline

A successful Phase 10 code run publishes `docs/data/odds_audit.json` with `historical_quotes_validated=0` until real, authorized quote files are provided. This is the **correct and expected result** and does not constitute a failed importer.
