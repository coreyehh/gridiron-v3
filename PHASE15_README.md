# GRIDIRON 3.0 — Phase 15: authentic 2026 NFL roster identities

Phase 15 uses the official **nflverse data release** for *season-roster data*, not a mock roster, and preserves the distinction between player identity and confirmed gameday availability.

## Source
- `https://github.com/nflverse/nflverse-data/releases/download/rosters/roster_2026.parquet`
- Fetch via `scripts/phase15.py`; source URL, SHA-256 of downloaded Parquet and UTC retrieval timestamp included in aggregate audit.
- Expected fields: `season`, `team`, `full_name`, `gsis_id`. Fail closed on missing schema or missing IDs. Exact season is required. Team aliases are normalized.
- Private per-player records include `player_name`, `team`, `season`, `player_id`, `source`, `source_ref`, and `as_of_utc`; these are the fields required by Phase 14 identity join.
- The downloaded roster lives in ignored `private_data/` on the GitHub runner, and is **not uploaded as an artifact**. Only aggregate counts, source hash and date are uploaded.

## Temporal integrity
A season-roster release may be updated after a game. Its retrieval timestamp indicates only **when we retrieved the file**, not the validity of old team assignments. It MUST NOT be used to retroactively verify roster membership on an older quote. Phase 14 checks that `as_of_utc <= captured_at_utc` and fails otherwise.

A unique GSIS match with name, team and season establishes an **identity match only**. `ACT`-like status on a season roster is NOT a validated final gameday inactive/active report. This phase cannot assert that any identified player actually appeared, was active, was offered by a particular bookmaker or played for the listed team at the kickoff time unless an independently timestamped game-specific source proves it.

## Run
GitHub → Actions → **GRIDIRON Phase 15 authentic roster validation** → Run workflow (branch `main`). The action runs offline fixture tests, retrieves the **real** 2026 roster release and publishes a seven-field aggregate report in an artifact named `phase15-roster-coverage-summary`. It makes zero The Odds API calls.

## Production integration gates
- A roster crosswalk must be fetched **before** a new live quote snapshot, not joined retrospectively to Phase 11's already collected October 12 quotes.
- A trusted team-week game-day injury/active report must be separately ingested and timestamped before treating any player as verified eligible.
- A verified NFL game schedule and mapping for each sportsbook event must be established; matches based on event home/away names alone are insufficient for wagering.
- Matchup-specific pregame projections and real offered-line probability calibration remain missing.
- Phase 14's private board stays **INSUFFICIENT_DATA**; no +EV or ROI claims.

## Status
Implementation committed. A **successful real GitHub run** is still required to confirm 2026 release availability, actual schema, source hash and populated player count. Do not call Phase 15 operational until that has been checked.
