# GRIDIRON Phase 25: Real-market price integrity & betting eligibility gate

## The goal
Phase 24 produced initial probabilities at **illustrative** thresholds only. Phase 25 adds rigorous two-sided sportsbook market normalization and a blocked-by-default eligibility process. It deliberately **does not** claim a profitable strategy, validate prices on postgame outcomes, or decrypt the user's old Phase 19 archive.

### Implemented
- Verify a book's over/under outcomes have exactly the same event, player, market, threshold, bookmaker, UTC quoted time, captured time and kickoff.
- Reject missing, stale (>60-minute quote age), future-dated, invalid-price or postkickoff offers.
- Calculate American-odds break-even, combined hold, two-sided no-vig fair-price *reference*, hypothetical EV only when a separately validated P(win) is supplied.
- No sportsbook edge is inferred from a difference between an uncalibrated point projection and book line. No claim that no-vig probability is model win probability.
- Block all qualifications without a **locked pre-quote projection**, independently calibrated probability at the **actual** market line, verified player ID, official game-day active status, verified role context, and a valid same-book two-sided pair.
- User-friendly workflow defaults to **offline/no API credits**: runs previous phase regression tests plus new market integrity tests, publishes only aggregate counts.
- Optional one-game real market evidence request requires setting `request_real_book_odds=true` manually and uses the saved `ODDS_API_KEY`. Captures genuine lines transiently in the runner, but does NOT print, save or upload player-level quotes; only aggregate evidence counts and quota remaining. Matchup team codes are optional; omit both for the next future NFL game.
- **No encryption key required and no downloads / Terminal setup.**

### Run
[Phase 25 GitHub Actions](https://github.com/coreyehh/gridiron-v3/actions/workflows/phase25-market-gate.yml)

Recommended first run: `request_real_book_odds=false` to validate all arithmetic and fail-closed rules at zero sportsbook credit cost. Set it to true only if you deliberately want the one-game live quote audit and confirm remaining credits.

After running, tell ChatGPT `complete` and the assistant should read the workflow summary and errors directly.

### Not yet implemented; required before actionable picks
- Historical or pregame-time locked Phase 23 projections joined to real odds snapshot before quote.
- A separate *verified point-in-time* active/role/injury feed.
- Real-line probability calibration and honest post-lock forward validation against official completed-game outcomes.
- Verified outcomes and a pregame ledger that grades only explicit final official selections.
- Book-specific distributions and any derived EV must stay in a permitted private delivery route, never public-repo artifacts.

A public GitHub repo makes sportsbook licensing, quote visibility and confidential data handling important. Phase 25's public summary is aggregate evidence only. A human-friendly presentation of exact live sportsbook lines will require an explicitly authorized, non-public interface with compliant data access; never publish raw sportsbook exports in public artifacts.
