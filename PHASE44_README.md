# GRIDIRON Phase44 — Projection quality and historical quote-integrity gate

Phase44 audits the immutable supplemental Phase43 Week6 12-fixture / 347-player passing-rushing-TD research snapshot, with a **readable** CSV quality report for every player. It flags unusually high workload or output, unexpected positional usage, no official actives, role uncertainty, zero recorded TD means incorrectly interpreted as impossible scores, uncalibrated TD tails and insufficient games.

Run [Phase44 GitHub workflow](https://github.com/coreyehh/gridiron-v3/actions/workflows/phase44-forecast-quality.yml) on main with existing `original_phase41_run_id=39142645209`. The workflow performs **zero** Odds API requests, imports the existing encrypted 307 receiving market ledger using `QUOTE_ARCHIVE_KEY`, verifies its lock digest, and produces two separate artifact families.

**Public:** `forecast_quality_review.csv` and `public_summary.json`. They contain the model's estimates and heuristic QA flags only. No individual sportsbook lines or odds.

**Encrypted private:** `private_market_reconciliation.fernet`, authenticated with the same original Fernet archive key. Contains historical original Phase31 receiving forecasts + bookmaker prices and lookup to Phase43 player identity on matching game and team. Phase43 does *not* itself forecast receiving yards/receptions, so its matching records never have a new receiving market projection or valid edge. This is a separate schema from Phase40/41, requiring dedicated local decryption support; previous HTML viewer may not display it.

**Temporal integrity:** Phase43 Week6 supplemental forecasts were frozen October18 16:24:30 UTC after the October18 15:55 UTC FanDuel quote capture. Their comparisons **cannot be called prospective**, even if both were made before Sunday kickoff. Preserve both original timestamps and forbid new calibrated win probability / projected market edge.

**What this does not prove:** No official verified game-day active status, injury report, route share, QB starter status, defensive coverage, valid market distribution, validated SGP prices, or bet approval. Heuristic flags are only review priorities. The Phase43 snapshot remains immutable, and no retrospective reforecast is used for real wagering performance.

Next: build a reproducible *next-slate* model freeze **before** fresh odds, incorporate official actives and role certainty with source verification, and evaluate well-calibrated passing/rushing/TD distributions on multiple completed weeks before making ranked betting claims.
