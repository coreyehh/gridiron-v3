# GRIDIRON Phase 36 — Game-day source provenance & parlay dependence

This phase adds **three concrete research subsystems**. It deliberately does **not** turn unverifiable status reports or unsupported joint probabilities into betting recommendations.

## 1. Player status source validation

`provenance()` inspects source category, HTTPS URL, source-record hash, event and player identifiers, retrieval time, and kickoff time. Claimed status ACTIVE / INACTIVE / OUT is **not authenticated merely because these fields are present**. No official NFL source fetcher / signature attestation currently exists in the repository, so every manually passed record is source-unverified and **cannot unlock a play**. Current roster and third-party injury reports are identity/context signals, not authentic NFL pre-kickoff active designations.

## 2. Empirical dependence research

`paired_binary_dependence()` requires two observed historical outcomes linked to a fixture/week. It measures both-hit rate, conditional P(B|A), single-leg empirical hit rates and the hypothetical independence baseline for comparison. It requires >=150 paired observations across >=6 distinct weeks even for **descriptive** readiness. Same-game pairs are not estimated from product of their singles. The result is not necessarily prospectively calibrated (overlapping player/fixture samples, nonstationarity, injury risk, market selection), and lacks FanDuel book acceptance and real combined payout. This phase supports the **research foundation** for 2–5-leg parlays, but does not implement a validated multivariate 2–5-leg conditional joint distribution yet.

## 3. Private quote integrity commitments

`freeze_private_quote_hash()` takes FanDuel-only rows supplied locally, validates pre-kickoff timing and hashes the canonical raw data. It can write **only an aggregate digest to `private_data/`**, never individual licensed odds/lines to the public repository or Actions logs. This is not encrypted archival and is **not a durable way to access prior player quotes later**; auditability requires a separate authorized private data store with retained originals.

## Run it

[Phase 36 one-click action](https://github.com/coreyehh/gridiron-v3/actions/workflows/phase36-evidence-chain.yml)

Select `main`; default bankroll $1000 and unit percent 1. GitHub runs all regression tests and emits an aggregate evidence status artifact. **No Odds API requests or credits.**

## Remaining blockers to actual FanDuel singles and 2–5-leg portfolios

- Integrate **authentic NFL game-day inactive source** with fetched source content, exact fixture/player ID, timestamps and real source authenticity validation; retain the source at the time of the decision.
- Independently evaluate model probabilities against **actual pregame FanDuel thresholds** over sufficiently many future games/weeks, with player/market dependent calibration, proper sampling uncertainty and missing-box-row bias resolution.
- Implement jointly validated **2–5-leg outcome simulations** and verify bookmaker-generated FanDuel SGP prices and leg acceptance—never multiply stand-alone odds.
- Create appropriately secured persistent storage for player-specific quotes and official pregame picks; public GitHub Actions artifact is not an acceptable private odds database.
- Retain frozen official picks and reconcile postgame outcomes, CLV, ROI, exposure and corrections.

**Until these gates pass:** zero official selections, zero units committed, and no estimated realized ROI.
