# GRIDIRON 3.0 — Phase 24: Participation evidence + honest probability calibration

## Purpose

Phase 23 won by small margins on player receiving predictions. Phase 24 probes whether those point predictions can be converted into **calibrated outcome frequencies**, while refusing to infer genuine game-day availability from roster snapshots or missing box-score rows.

### Implemented now

- For each completed 2026 week from Week 4 forward, forecast targets, catches and yards using **Phase 20 team passing volume + Phase 23 target-share challenger**.
- **After** forecasting but **before** revealing the target week's actual game outcomes, score probabilities for fixed example receiving markets: receptions thresholds 1.5 / 2.5 / 3.5 / 4.5 / 5.5; receiving-yard thresholds 24.5 / 39.5 / 54.5 / 69.5 / 84.5.
- Calibration method: smoothed empirical historical Phase 23 residual frequency, using **only completed earlier weeks**. Requires >=50 previous residuals per market or emits **no probability**.
- Report Brier score (lower is better), expected calibration error (ECE), and population frequencies by probability bin; compare with a fixed 50% probability reference only. The reference is deliberately weak, **NOT** a sportsbook or properly trained baseline.
- Explicitly fail the participation-evidence gate: nflverse roster = verified identity, NOT actual game-day status. Missing game row = ambiguous, not proof of inactive player. Per-route participation, snaps, official injury confirmations, and opponent coverage are NOT available here.
- No sportsbook API calls, lines, prices, implied probabilities, no-vig adjustment, +EV classification, stakes or bets. This is not a bookmaker calibration or ROI test.
- All publicly published reports contain only aggregated evaluation metrics, no licensed sportsbook odds.

### Running

[Open Phase 24 validation in GitHub Actions](https://github.com/coreyehh/gridiron-v3/actions/workflows/phase24-calibration.yml).

Select branch `main`, leave `run_real_data` checked, `first_week=4` and `last_week=18`, and click **Run workflow**. It automatically skips unfinished weeks. No keys, Terminal, file downloads or paid credits required.

The GitHub run summary shows the actual calibration scores, and a public aggregate JSON artifact is saved for 30 days. Return to this chat with `complete`; the assistant can inspect the live results directly.

### Critical remaining work

- **Participation:** Obtain point-in-time official game-day actives and a legitimate source for player snap and route participation, preserving source timestamps. Don't fabricate these features from nflverse player-week receptions/targets.
- **Market:** Integrate user-authorized bookmaker quotes and **actual recorded offer timestamps** in a compliant, private workflow (not public GitHub artifacts). Require exact player, game, market, line, side, price and captured-before-kickoff status.
- **Calibration:** Evaluate conditional distributions on contemporaneous real bookmaker thresholds, using independent holdout/forward validation and a properly trained baseline. Distinguish point accuracy, calibration, and financial performance. Reject false 'edges' when data are missing.
- **Model selection:** Do not treat a better Brier score against a constant 50% reference as proof of a viable betting model.
