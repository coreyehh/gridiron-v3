# GRIDIRON Phase 40 — Actual captured market vs frozen prediction vs postgame outcomes

**Purpose:** use the *existing encrypted* Phase39 FanDuel event quote archive. Do not spend new Odds API credits. The workflow pulls the historical artifact from run 39049308856, decrypts it only in ephemeral runner memory using `QUOTE_ARCHIVE_KEY`, and creates a **new encrypted point-in-time matched-prop research ledger**. Only an encrypted ledger and anonymous aggregate counts are uploaded to public GitHub Actions artifacts. Save the encrypted artifact externally before the 30-day expiry.

## Run immediately (pregame, zero API credits)

[Phase40 GitHub workflow](https://github.com/coreyehh/gridiron-v3/actions/workflows/phase40-prospective-ledger.yml)

Choose `main`, `archive_run_id=39049308856`, and leave **grade_completed=false**. The workflow runs all regression tests, downloads the already-encrypted original archive with the built-in read-only GitHub token, checks the exact Phase31 SHA-256 and game/time boundaries, reconciles same-book same-player same-line over/under pairs, and writes:

- Public `public_aggregate.json`: number of successful matches, rejection reasons and integrity checks **only**; no player names, lines, odds or encrypted keys.
- Protected `locked_ledger.fernet`: for each eligible matched RESEARCH row, frozen projection, actual captured FanDuel over/under line and price, bookmaker source timestamp, fixture, name-matched player ID, all qualifier statuses explicitly false. Fernet ciphertext is not plaintext; possession of key + artifact can reveal lines.

**Player matching uses unique normalized names inside an exact game; it is NOT bookmaker-to-GSIS authenticated identity.** A matched two-sided quote is not a qualified bet and not proof of profit. Every candidate is explicitly research-only, no EV and 0 units.

## After the selected matchup is final

Run exactly the same workflow with `grade_completed=true` **only when the particular game is completed**. It fetches fresh nflverse schedule and 2026 player-week stats, verifies home+away, week, date and both final scores, then grades the archived lines using that independent box row. Absent player-week stats stay unresolved/UNKNOWN, NOT under/zero. Ties at integer lines are PUSH. This grades BOTH sides of a listed market *as hypothetical outcomes*; since no bet was officially locked it does not calculate realized ROI, units won, or CLV.

It writes encrypted `settled_ledger.fernet` when a verified final is available, and a public summary containing aggregate graded/unknown counts only. If not final, it outputs `WAITING_FOR_VERIFIED_FINAL`, without retroactive bets.

## Accuracy caveats

- The original pregame forecasts stay immutable and cannot be changed to improve scored results.
- Bookmaker odds, offered lines and player names are not published as open GitHub artifacts. Key never printed.
- Provider player IDs are not authenticated; names require an exact unique match.
- Bookmaker price captured before kickoff does not equate to closing line. CLV requires a separately timestamped later quote.
- Historical calibration is not solved by one event. Do not claim the model is calibrated or issue positive EV bets from this ledger.
- NFLverse player box feeds may be delayed after the fixture final; unknown rows remain unknown.
- Official NFL active/inactive and route status still need authenticated fixture/player evidence.
- Never delete `QUOTE_ARCHIVE_KEY` until all archived captures have been decrypted/re-encrypted elsewhere; losing it destroys retrieval.

This is a prospective evidence **collection, preservation and outcome matching** subsystem. Not an automated sportsbook wager executor.
