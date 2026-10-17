# GRIDIRON Phase 33 — Probability and official participation evidence

**Goal:** distinguish a point projection from a dependable probability at a bookmaker's exact offered player line, and reject guesses about whether a player is active.

## What is implemented

1. Reconstruct Phase23 receiving predictions using completed prior weeks, matching the earlier Phase24 research architecture.
2. Accumulate prior **forecast residuals** and estimate smoothed frequencies at fixed, **illustrative** thresholds. Within each target week, all outcome information is withheld until after predictions are scored.
3. Use a minimum residual history of 100 observations and show a 95% Wilson *sampling* interval for exceedance frequency. This interval is not a full player-level prediction interval: game scripts and players are dependent.
4. Evaluate Brier score, ECE and diagnostic observed base-rate Brier on observed player-week box rows; exclude missing rows as unverified—not zero, not confirmed inactive.
5. Report the evidence gate. At least six evaluated weeks with out-of-sample probability scores and at least 500 evaluations per receiving market are needed before an initial research sufficiency gate, with further prospective validation still required.
6. A fail-closed official-player availability gate: the current repository has **no authenticated, event/player/time-matched official gameday actives feed**. A boolean or season roster identity is *never* accepted as confirmation.

## Deliberate limitations

- No bookmaker/player quotes are fetched; **zero Odds API credits**. The completed Phase32 live aggregate cannot reconstruct individual bookmaker lines or historical odds in public.
- The historical test lines are NOT actual sportsbook prices. Real-line calibration, time-stamped paired price history and independently validated over/under predictive performance still need separate infrastructure.
- An early two-week calibration score is only preliminary. The observed outcome base-rate comparator in this implementation is in-sample and only a diagnostic.
- Missing box rows excluded from scored outcomes can create survivorship bias; this must be resolved using official game-day inactive and participation records.
- No direct weather, route, OL, coaching or verified same-day player participation feed exists in this phase; do not infer these from rosters.
- **Production promotion: none. Qualified bets: zero.**

## Run

[Phase 33 one-click GitHub workflow](https://github.com/coreyehh/gridiron-v3/actions/workflows/phase33-probability-evidence.yml)

Choose branch main; leave `run_real_data=true`, first week 4, last week 18; click **Run workflow**. GitHub reports the historical audit in its job summary and uploads an aggregate JSON report. No sportsbook credits, encryption secrets, or Terminal.

**Next required engineering:** verified official player-inactive source and provenance tied to game and kickoff, private time-stamped real bookmaker line snapshots and independent evaluation of calibrated probabilities exactly at these quoted lines. Those gates must pass before publishing qualified picks.
