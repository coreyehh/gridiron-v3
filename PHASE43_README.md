# Phase 43 — Actual Passing / Rushing / Touchdown Forecast Baselines

Phase 43 is a **new model**, independent of bookmaker markets.

It downloads source-hashed nflverse 2025 and completed 2026 player-week parquet, the official-style schedule file used in Phase31 and the 2026 roster, then forecasts only players with at least three observed prior games on a fixture team. Each metric uses shrunk recent per-player observed box means (last five games, with a baseline). Passing yards / attempts / completions / interceptions / passing TDs, rushing yards / attempts and receiving/rushing TD counts are supported.

For *total scoring TDs* (rushing + receiving), Phase43 derives provisional anytime / 2+ / 3+ touchdown probabilities using an **uncalibrated Poisson count assumption**, with the mean drawn from observed scoring games. These are exploratory tail signals, not NFL-calibrated fair odds or safe bets. Passing TDs are tracked separately from individual player scoring TDs.

To prevent look-ahead, Phase43 uses **only completed prior 2026 weeks**, and refuses to freeze a new target week while any earlier week is unfinished. It locks the point-in-time future-only projection digest at `snapshots/phase43/2026-week-NN.json` if eligible, and never overwrites an existing lock. It runs observed-player-row-only historical diagnostics and does not invent zeros for players absent from a box source. Historical backtests are imperfect and not point-in-time publication attested.

[Run Phase43 workflow](https://github.com/coreyehh/gridiron-v3/actions/workflows/phase43-multimarket-forecasts.yml): choose main and `target_week=0`. For a still-in-progress Sunday Week6, it may correctly respond `WAITING_FOR_COMPLETED_PRIOR_WEEK_OR_FUTURE_GAME`; do not override this gate simply to force picks. If the prior week is complete, it can produce next week's future-only snapshot. Run again after full final game completion and source publication.

**No new Odds API credits**, no bookmaker lines required, and no GitHub private archive decrypted. There are no qualified wagers/units, no validated single-line probability calibration, no opponent/player-specific official availability, no authenticated game-day route/injury sources or accepted SGP pricing. TD Poisson is a baseline only and needs out-of-sample touchdown-tail calibration and better red-zone concentration / role evidence before bet qualification.

Phase42 expanded **market ingestion**, Phase43 begins **projection creation**. Phase44 should compare frozen Phase43 distributions with authentic fresh FanDuel quotes for *next* week, not apply new calculations retrospectively to already priced Week6 games.
