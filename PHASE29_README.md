# GRIDIRON 3.0 — Phase 29: Route participation readiness and opportunity quality

The requested high-value signal is **routes run per team dropback**, enabling targets per route run and RB/TE pass-protection-versus-route roles. An offensive snap is NOT a route. This phase checks a publicly documented participation release for current-season coverage but DOES NOT make the unsupported leap from player presence on a play to a verified route count.

### Evidence status
- [nflverse documentation](https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html) states that FTN-sourced **play-by-play participation** data since 2023 is published only **after the postseason**, not updated during the season. Phase 29 probes the 2026 parquet URL to record availability but does not treat it as validated routes.
- 2026 historical **offensive snap counts** sourced from PFR through nflverse remain available (from Phase 28); 2026 player-week **targets** from NFLverse.
- We compute `targets / offensive_snaps` for each previously observed game with safe name+team crosswalk; **never** call it targets/route.
- Fixed challenger: recent 2-game target-per-offensive-snap rate versus trailing 5 (minimum 3 matched completed prior games), clip ratio to .75–1.25 and take only 20% of difference (0.95–1.05 factor). Missing source = neutral multiplier. This is a *heuristic research challenger*, not a promotion.
- Walk-forward Phase23 versus challenger on the identical player-game sample, comparing targets, receptions, receiving yards with descriptive diagnostics. Same-week targets and snaps excluded from all target-week features.
- No official injury/active status, pass-protection responsibilities, actual routes, player alignment, coverage, bookmaker prices, calibrated market probabilities or qualified picks.

### Run
[Phase 29 GitHub Action](https://github.com/coreyehh/gridiron-v3/actions/workflows/phase29-route-readiness.yml)

Select branch main, leave `run_real_data=true`, both team fields empty, week `0`; click Run workflow. GitHub job summary shows real source availability, matchup forecast challenger and retrospective accuracy metrics. No sportsbook API credits, local setup, Terminal or encryption.

**Decision:** Do not promote even if an initial short historical test improves. We need reliable true routes and prospective testing.
