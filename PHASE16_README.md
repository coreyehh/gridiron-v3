# GRIDIRON 3.0 — Phase 16: Prospective sportsbook-to-roster identity audit

## Deliverables

- `scripts/phase16.py`: a real **roster-first** pipeline that collects a fresh 2026 nflverse roster, then (only with `--live`) requests a single upcoming NFL game's receptions / receiving-yards lines from The Odds API, and compares unique sportsbook player names against GSIS IDs.
- `test_phase16.py`: tests for all 32 team name mappings, player counting versus outcome counting, same-name collisions, timestamp constraints, and aggregate-only report.
- `.github/workflows/phase16-validation.yml`: manually dispatched GitHub workflow. Default unchecked runs **offline tests with zero Odds API credits**. The `use_api_credits` checkbox executes a one-event live integration and uploads **only anonymous counts**.

## Strict data ordering

1. Retrieve season roster before downloading odds. Capture roster file SHA-256, source URL, and actual UTC acquisition timestamp. The roster stays in `private_data/`, which is Git-ignored.
2. Request up to two NFL prop markets for one event and four US books, only with explicit opt-in. This consumes API credits (historically two per request, but actual cost must be checked from the returned quota).
3. Require roster retrieval no later than quote snapshot, quote snapshot strictly before kickoff, matching NFL season, and recognizable complete team names → nflverse team abbreviations.
4. Group sportsbook outcomes by **event, season, normalized player name** before tallying matched, unresolved, or ambiguous player **identities**. One player with over/under outcomes from several books counts only once.
5. Report identity coverage, quote outcome volume, sportsbook list, quota headers, roster fingerprint and number of unresolved/ambiguous names. **No player names or betting lines are published in GitHub artifacts**.

## What a match proves (and does not prove)

An exact name + matchup teams + season match in nflverse establishes a current roster **identity match**, not an official game-day active status. If both opponents have players with the same normalized name, the result is **AMBIGUOUS**, not a falsely assigned player ID. An identity match alone does not certify that team assignment was accurate on kickoff day; the season roster snapshot may lag official transactions. The workflow does not fetch official inactives, does not supply matchup projections, and does not calculate calibrated real-offered-line probability or betting EV.

The previously captured Phase 11 odds snapshots are intentionally NOT retroactively verified using a roster acquired afterward. Each Phase 16 integration collects a new roster first.

## How to run

GitHub Actions → **GRIDIRON Phase 16 prospective identity match** → Run workflow on `main`.

First keep **use_api_credits unchecked** to run the 9 offline tests (plus existing Phase 15 and Phase 11 tests). Then opt in once with the checkbox checked and region `us`. Download `phase16-identity-match-report` (14-day retention) to inspect aggregate live match coverage. The workflow cannot be automatically started through the currently available GitHub connector.

## Decision policy

Always `decision=INSUFFICIENT_DATA` and `bets_qualified=0`. The current model still lacks authoritative NFL game-day actives, real pregame projection preparation, calibrated sportsbook-line probabilities and authentic prospective settlement evidence.
