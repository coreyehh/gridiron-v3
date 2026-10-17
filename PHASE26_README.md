# GRIDIRON Phase 26 — Integrated matchup research

Phase 26 combines genuine nflverse **2025/2026 player-week and schedule data**, Phase20 team pass/rush forecasts, Phase23 adaptive target shares, preliminary Phase24 empirically observed residuals, and optional Phase25 real-book **coverage counts** in **one readable GitHub run summary**.

## How to run

[GRIDIRON Phase 26 integrated matchup research](https://github.com/coreyehh/gridiron-v3/actions/workflows/phase26-matchup-board.yml)

1. Choose branch `main`.
2. Keep `run_real_data=true`.
3. Leave both teams empty and week `0` to automatically select the first game with a schedule date strictly later than today's UTC date. To select a particular game, enter both valid team codes and its 2026 regular-season week.
4. Leave `request_real_book_odds=false` to use **zero paid odds credits**. Turning it on makes ONE sportsbook request for exactly the selected game and publishes only matched-quote counts.
5. Click Run workflow. The completed Actions job shows the public player research board and offers an unencrypted JSON artifact. No Terminal, manual files, or encryption keys.

## Evidence and limitations

**Sources:** Actual league-wide nflverse player-week stats, current 2026 roster identity snapshot, schedule. Historical predictions only use scored weeks before the target; source SHA-256 hashes are recorded. Strictly future-date auto selection avoids uncertain same-day kickoffs. A date is **not** an official exact kickoff verification.

**Current models:** Team attempts = Phase20; player target/catch/yards = Phase23 candidate; illustrative over probabilities at 3.5 catches and 54.5 yards from past Phase24-style empirical forecast residuals, when at least 50 prior historical residuals exist. Unavailable sample results in `null`, not invented probabilities. The Phase22 team-volume adjustment was studied separately and is **not integrated** in this forecast yet; integration would require a properly frozen prior-error training pipeline.

**Public output:** Plaintext reports show players' public nflverse-derived forecast counts and probabilities at illustrative statistical thresholds, **not licensed live bookmaker odds or wagers**. Optional bookmaker audit fetches one match and prints only safe aggregate coverage counts; licensed individual lines are not persisted to GitHub.

**Not established:** Official actives, player routes/snaps, opponent schematics, current day injury status, exact gameday player availability, probability calibration at *current real bookmaker lines*, joint prop distributions, value-versus-price or sportsbook-profitability. Not even a high model projection is an official pick. Qualified bets = zero. Historical probability estimates may be weak and retrospectively chosen, with no guarantee of generalization.

This phase integrates research components but deliberately **does not manufacture actionable +EV picks**. Real-book decisions require permitted private data custody plus outcome-verified prospective calibration against authentic timestamped book lines.
