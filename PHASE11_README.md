# GRIDIRON 3.0 — Phase 11: Live Market Board

## Scope / current reality

The free API pilot proved that The Odds API returned NFL reception and receiving-yard props for FanDuel, DraftKings, BetMGM and BetRivers. This phase transforms one authentic **pregame event response** into normalized per-player, per-book, per-market over/under quotations; it does NOT magically create an actionable betting model or authenticate a player's NFLverse identity.

Code:
- `scripts/live_market.py`: quote normalization, UTC timestamp validation, exact market maps, break-even arithmetic, uniqueness checks, no fabricated P(win)/EV.
- `test_live_market.py`: no-leakage pricing tests, duplicate and bad quote rejection, positive/negative American odds.
- `.github/workflows/live-market-probe.yml`: manual-only workflow; default runs tests without spending credits; user may opt into **one** live event API call (two markets). Its raw quotes remain only on the ephemeral GitHub runner and are **not uploaded or printed**.
- `docs/index.html`: in-browser local JSON reader; raw lines never leave the user's browser.

## To run

Open the **GRIDIRON Phase 11 live market board probe** workflow in GitHub Actions.
Keep `spend_credits = false` for the first test-only run. To inspect a real API integration, run again with `spend_credits = true`, which consumes API credits for one NFL game's two markets and uploads a summary-only artifact.

`python scripts/live_market.py --fetch --region us` works locally with `ODDS_API_KEY` set (DO NOT paste credentials into public repositories, logs or ChatGPT). It writes `private_data/live_market.json` (ignored by Git) for local viewing. A locally produced JSON file can be selected in the dashboard using **Load a local quote snapshot**, which reads the file entirely within the browser.

## Why we don't publish actual odds yet

**Your GitHub repository is PUBLIC.** GitHub workflow artifacts and Pages assets can be viewed by others; publishing licensed player-level feeds and private wagering research may violate terms or expose sensitive records. This experiment stores no private market rows in the repo or public run artifacts. To make the market board permanently hosted with current per-player lines, choose approved terms-compliant storage and a private backend with a server-side API key (not browser JavaScript and not static GitHub Pages). A private repo by itself does not make GitHub Pages data access-controlled for all plans.

## Data fields

One outcome row includes event ID, home/away teams, kickoff, player display name, unverified NFLverse ID, market, side, line, bookmaker, odds, quote timestamp, capture timestamp, implied break-even probability, and explicit decision state.

No join to NFLverse `player_id` is attempted from ambiguous player display names; a verified crosswalk with player IDs must be built before automated grading.

## What is required before BET

1. Verified name/event/player ID mapping; reject unresolved names and reused identities.
2. Pregame-only calibrated probabilities built without same-game leakage.
3. Verified live prices and quote freshness for every candidate, book-specific vig and alternate lines.
4. Explicit outcome-first, price-second decision gate and versioned pick snapshot before kickoff.
5. Independent official results with deterministic pushes, ungraded states and full accountability.
6. Licensed/provider-approved handling of odds data and a safe persistence architecture.

**Until then: all picks display INSUFFICIENT_DATA, not +EV.**
