# GRIDIRON Phase 27 — Real historical matchup context and honest validation

Phase 27 adds **only context supported by currently accessible authentic sources** to the integrated Phase26 board:

- Schedule-based **home/away** and **calendar days of rest** from the NFLverse schedule. Rest is descriptive only; there is no empirically tested rest multiplier.
- Prior opposing offenses' **WR/TE/RB target shares when facing a defense** (last five 2026 completed games), derived from NFLverse player-week stats and actual schedule opponent pairings. This indicates position-level **opportunity allowed**, *not* coverage assignment or efficiency.
- Prior league-wide position target share as a reference. Apply a conservative, fixed challenger multiplier of **0.95–1.05** with 20% of bounded target-share deviation. At least three defensive exposure games required. Apply it to Phase23 player targets, receptions and yards as a **challenger only**; original Phase26 forecasts remain intact.
- Historical walk-forward comparisons of same-player receiving targets, receptions and yards errors, with earlier completed weeks only. The adjustment is not promoted regardless of a small retrospective improvement, because the short evaluation window is not prospective validation.
- **Fail-closed, explicitly unverified:** official injuries, OL continuity, game-day active designations, routes/snaps, defensive coverage shells, weather, officiating and current sportsbook odds. Do not manufacture these sources.

## Run

[GRIDIRON Phase27 GitHub Actions](https://github.com/coreyehh/gridiron-v3/actions/workflows/phase27-matchup-context.yml).

On branch `main`: keep `run_real_data=true`, leave team codes blank and `week=0` for the next future-dated matchup, then click Run workflow. Tests and a real-data walk-forward benchmark execute. The job summary displays a readable matchup and the model-versus-challenger accuracy.

No API credits, files to download, encryption keys or Terminal. Only public NFLverse-derived player projections in the public artifact.

## Interpreting it

This is not a true film/schematic defensive matchup grade. A position's targets against prior opponents may reflect previous opponents' offensive tendencies and game scripts, not a stable causal defense property. The fixed heuristic requires prospective testing. Phase27 does not estimate calibrated player-prop probabilities for actual sportsbook thresholds and produces **zero qualified bets**.
