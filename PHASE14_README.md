# GRIDIRON 3.0 — Phase 14: Authentic Quote Evidence Bridge / Private Ledger

## Delivered
- `scripts/phase14.py`: offline ingestion of private Phase 11 sportsbook quote JSON, separately sourced current-season roster crosswalk, and versioned point projections; strictly reconciles event/player/market and pre-kickoff timestamps. Writes private `private_data/phase14_board.json` with a SHA-256 audit fingerprint.
- `test_phase14.py`: eight tests for identity ambiguity, stale roster evidence, projection-timing leakage, pre-kickoff cutoff, and explicit official-pick settlement states.
- `.github/workflows/phase14-validation.yml`: manual, zero-credit GitHub workflow testing an entirely **synthetic** fixture. It does **not** fetch real lines, roster records or run the real player projection model.
- `scripts/live_market.py` now includes `season` (derived from NFL kickoff year and Jan/Feb postseason rule) and `season_source` on each normalized quote. This must still be reconciled against official game schedule for real-world usage.

## Inputs and strict gates
Input files are local private JSON. The quote snapshot must have `quotes: [..]` and each row from Phase 11 contains event ID, season, matchup teams, player display name, market, side, line, American odds, quote time, capture time and kickoff.

Roster input must be an array of player records each carrying `player_name`, `team`, `season`, `player_id`, `source`, `source_ref`, and `as_of_utc`. A name is joined only when **exact normalized name, valid matchup team, explicit season, unique player ID, provenance, and as-of timestamp** all agree. It is labeled `IDENTITY_MATCHED_NOT_ACTIVE_VERIFIED`—not an official NFL active designation. The project has **NOT yet acquired or populated a verified current-season roster file**.

Projection input must be an array of predictions each carrying `event_id`, `player_id`, `market`, `point_projection`, `model_version`, `input_snapshot_sha256`, and `created_at_utc`. It joins only when unique and generated no later than quoted odds timestamp. **A calibrated over/under probability is not inferred from a point forecast**. This project does **NOT** yet produce automatic, matchup-specific, authenticated current NFL projections.

No market quote is marked BET or +EV. Every row stays `decision=INSUFFICIENT_DATA`; there is no qualified betting ROI.

## Official pick grading helper
`settle_official_pick` grades only rows marked `status=OFFICIAL` with a pre-kickoff lock, an immutable snapshot SHA-256 reference, an explicit valid market, and separately provided officially sourced outcome. Push / win / loss unit accounting is supported as a deterministic **helper**, but this phase does not automatically certify sportsbook-specific settlement rules, player identification in postgame stats, or verify authenticity of a claimed `official` result. The helper does not write to any persistent master ledger by itself; the private board is a working research snapshot. Leans, candidate picks, unverified results and late locks must not count as official wins.

## Run and limitations
Run GitHub Actions **GRIDIRON Phase 14 private ledger validation** on `main`. It costs 0 The Odds API credits and uploads NO private data. For real offline use, with your own safely sourced inputs:
`python -m scripts.phase14 --snapshot private_data/live_market.json --roster private_data/verified_2026_roster.json --projections private_data/pregame_predictions.json --output private_data/phase14_board.json`.

**Current missing dependencies**: official current-season roster provenance and active status; real upcoming player-level projections, out-of-sample calibrated line probabilities against actual quoted lines; approved licensed private quote storage; automated durable snapshot storage and independent results-grade feed. Until these exist, this is a tested foundation, NOT a running wager-selection product.
