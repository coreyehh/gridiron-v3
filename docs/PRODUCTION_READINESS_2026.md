# GRIDIRON 3.0 — Production Readiness Gates (2026-10-26)

## Current verified state
- The NFLverse refresh workflow succeeded on 2026-10-20, but its checked-in workflow imports **2021–2025**, not 2026. Do not label 2026 ingestion complete.
- Phase31 accountability workflow succeeded 2026-10-26. Success means the job ran, not that wagers, odds or predictive calibration were validated.
- README states: "No live predictions or verified EV yet."
- Phase41 currently imports an encrypted ledger and explicitly marks its output RESEARCH_ONLY_UNVERIFIED_PLAYER_ACTIVES_AND_PROBABILITY.
- Prior chat-based game predictions are **qualitative** unless traceable to a frozen repository execution.

## Non-negotiable promotion gates
1. **Data:** Fresh, source-attributed, timestamped 2026 game logs, schedule, play-by-play, participation, depth charts, and injuries. Fail closed if unavailable or stale.
2. **Identity:** Verify opponent, team, player, starter, and game-date joins. Fail closed for traded, injured, or inactive players.
3. **Matchups:** Forecast every game with winner probability, median score, fair spread, total, underdog win probability, and 10+/14+/21+ point margin tails.
4. **Props:** Forecast attempts, completions, passing/rushing/receiving yards, receptions, TDs, and alternate lines using role, opponent-strength, scheme, game-state distributions.
5. **Markets:** Only source-stamped, book-specific FanDuel lines with capture time, market and selection identity. Missing quote => NO PRICE / NO EV.
6. **Calibration:** Walk-forward validation on past weeks only; track log loss/Brier for win probabilities, MAE and coverage for player distributions, ROI for frozen priced selections. Never use future data.
7. **Portfolio:** Compute probability/EV after price validation; correlated legs require joint probability and availability verification.
8. **Freeze:** Save pre-kickoff immutable projections and official bet promotions separately; preserve timestamp, code revision, source versions and odds.
9. **Accountability:** Grade all matchups and only *official* wager records for betting hit rate and ROI; maintain candidate diagnostics separately. Review upsets against pregame evidence, not hindsight.
10. **Dashboard:** Show input evidence → opponent-adjusted reasoning → distributions → prices → approved bets; display readiness and missing inputs prominently.

## Work sequence
- [ ] Inspect successful refresh artifact/manifest and document exactly which seasons, rows and dates it contains.
- [ ] Add 2026 season ingestion and deterministic schema/coverage tests, including nonempty latest-week assertions.
- [ ] Validate starter/role sources and official inactives; block unsafe player joins.
- [ ] Audit Phase31 snapshot generation and whether 2026 matchups are frozen before kickoff.
- [ ] Audit Phase47 odds provider and validation tests; identify whether real FanDuel quotes are available.
- [ ] Integrate full-slate matchup win/spread/total/tail probabilities into immutable snapshot.
- [ ] Build week-7 retrospective without overwriting original pregame forecasts.
- [ ] Add weekly accountability and ranked matchup + prop boards.
- [ ] Require a green end-to-end dry run before calling any selection a model-approved wager.

## Output contract
Each selection: `game_id, kickoff_utc, model_commit, data_asof_utc, player_id(optional), market, side, line, book, odds, quote_asof_utc, fair_line, probability, break_even_probability, expected_roi, confidence_interval, correlated_exposure, rationale, gate_status, approved_at_utc(optional)`.

Statuses: `RESEARCH_ONLY`, `DATA_MISSING`, `PRICE_MISSING`, `CALIBRATION_FAILED`, `ELIGIBLE`, `APPROVED`, `SETTLED`. Never conflate candidates with bets.

## Immediate corrective note
The October 25 Chiefs–Seahawks candidate board may be evaluated as directional predictions, but cannot be recorded as five official wins absent archived approvals and available prices.
