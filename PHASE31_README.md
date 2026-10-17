# GRIDIRON Phase 31 — Immutable Weekly Forecast Accountability

Phase 31 creates durable **pregame player-forecast snapshots** committed under `snapshots/phase31/2026-week-XX.json`. Subsequent runs **never overwrite these frozen forecasts**. When the *entire week* is scored in the nflverse schedule and the player box source is available, only frozen predictions are graded against observed box-score rows.

## Run
[Phase 31 GitHub Action](https://github.com/coreyehh/gridiron-v3/actions/workflows/phase31-accountability.yml). Choose main and week `0` (automatic), and press **Run workflow**.

The workflow also runs automatically every day at approximately 13:17 UTC, subject to GitHub Actions scheduler delays and organization settings. This is a public-data, no-fee workflow with **no sportsbook API credits and no encryption keys**.

**GitHub needs Actions write permission** to commit the pregame snapshot to main. If your repository restricts workflow commits, the step will fail, and **prospective durability has NOT been established**. Do not treat an uploaded artifact or uncommitted job output as a durable forecast lock.

## Protection
- Only future games with a gameday date **strictly later than current UTC date** and no final scores are included. Same-day games are intentionally excluded because their kickoff time isn't independently verified.
- Future fixtures are selected in the earliest relevant incomplete week. On partially completed weeks, only still-future matches are included. Only one snapshot file per week is stored; games omitted from the first file stay omitted (no retrospective backfilling).
- Requires all earlier regular-season weeks fully scored. Hashes the snapshot, source downloads and prior-week list; stores timestamp and source hashes in each immutable file.
- Duplicate week: read and hash-verify previous file, no replacements. A modified prior file fails rather than silently regenerating it.
- Grade *only once all game scores for the week exist*; do not infer whether an individual was active from a missing row.
- Missing player-week statistical rows are **unresolved/unknown** and excluded from the observed-only MAE; this selection limits representativeness.
- The ledger shows MAE for targets, receptions and receiving yards, weekly and cumulative, plus coverage. These **are not bet win percentages**.
- Scoring is recomputed against latest source data and reported in an Actions artifact; the underlying forecasts alone are immutable. A robust permanent postgame truth ledger will additionally need frozen postgame source snapshots or adjudicated revision audit.
- Current source-publication dates cannot be independently attested. The timestamp represents a GitHub-run forecast, not an independently verified point-in-time source archive.
- No official actives, routes, calibrated sportsbook probabilities, wagers, ROI or verified profit. Qualified bets = **0**.

## Operational details
The workflow runs its previous regression tests before live source acquisition. Files are committed to `main` only after running all gates. The Action's concurrency group prevents two Phase31 runs from updating the same snapshot simultaneously. Model champion: Phase23 player roles + Phase20 team passing volume, no unproven challengers promoted.
