# GRIDIRON Phase 42 — Passing, Rushing, Touchdown Market Expansion

The original Phase31 Week 6 frozen forecasts **only contain targets, receptions, receiving yards**. Phase42 adds real FanDuel **market collection** for:
- Passing: passing yards, attempts, completions, interceptions and passing TDs.
- Rushing: rushing yards and attempts.
- Touchdowns: anytime TD, first TD, 2+ TD and 3+ TD.

**Crucial:** Price discovery is not a projection. Phase42 does NOT fabricate passing/rushing/TD forecasts, model probabilities or qualified bets. New-market model fields are explicitly null. A validated predictive model for these markets requires a future phase, independently tested across completed NFL weeks and frozen before odds lookup.

[Run Phase42 GitHub workflow](https://github.com/coreyehh/gridiron-v3/actions/workflows/phase42-expanded-markets.yml).

## Recommended first run — free
Use branch `main`, keep `collect_live_extended_markets=false` and `max_new_events=0`. Set `prior_phase41_run_id=39142645209`. This preserves the previous **307 receiving-market pairs** in a newly encrypted archive, with no new paid API calls. It also executes 12 new regression tests plus earlier phase tests.

## Optional live market collection — paid API
Check `collect_live_extended_markets`, choose `max_new_events=1/3/6/13`, `region=us`. The workflow discovers only **future NFL games matching the original frozen Week6 schedule** and only captures at verified times **before kickoff**, after the forecast lock. Game-day event discovery and each event quote request can consume provider credits; requested markets vary by provider plan and bookmaker. Once Week6 kickoff passes, the frozen snapshot cannot be used for new game captures; Phase43 should create a fresh post-Week6 freeze for the next NFL week. Missing odds, unsupported TD market formats, and unverified player identities remain missing; no backfills.

**TD specifics:** Bookmakers often list an anytime touchdown `Yes` price without a paired `No` price. Do not synthesize opposite side or call the single quote a fair probability; 2+ and 3+ TD opportunities likewise require an independently calibrated score-count distribution and a validated price.

**Historical archive:** All existing Phase41 receiving pairs remain inside `original_receiving_entries`. New passing/rushing/TD quote sides are in `new_market_quotes` with no probability or eligibility until tested. Open both only after local decryption of the Phase42 `expanded_private_market_archive.fernet`, using the original `QUOTE_ARCHIVE_KEY`. The existing Phase40 viewer is not yet aware of this new Phase42 two-section schema—do not promise it will display all categories. Never print decrypted rows or key on public GitHub logs.

**Security & reporting:** GitHub public artifact is aggregate counts. Actual per-player prices and lines are encrypted with Fernet; 30-day artifact retention. Do not mistake a successful workflow for bets approved. No unit allocations or parlays.
