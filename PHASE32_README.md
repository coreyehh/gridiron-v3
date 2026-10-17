# GRIDIRON Phase 32 — Frozen forecast vs current real-market integrity

This integrates the **immutable Phase31 Week 6 snapshot** (locked on October 17, 2026) with existing Phase25 live Odds API market normalization and book validation. This phase is a **research market-comparison audit**, not a betting pick or payout recommendation.

## One-click operation
[GitHub Phase32 Action](https://github.com/coreyehh/gridiron-v3/actions/workflows/phase32-market-matching.yml).

- Run with `request_real_book_odds=false` first: all offline tests and snapshot integrity checking, **zero sportsbook credits**.
- For the one-game live audit, explicitly check `request_real_book_odds=true`, optionally set a provider `event_id`, select region, and run. Requires pre-existing `ODDS_API_KEY` repository secret. It discovers current NFL events, selects **only** an exact matchup and compatible date from the immutable Week6 snapshot, and makes **at most one paid per-event props odds request**, never a full 13-game slate or retrospective odds call. If none of the frozen events remain upcoming, it reports no eligible event without a paid call.
- **No bookmaker odds, book/player/line combinations, or individual gap/price pairs are printed, committed, or uploaded.** Raw quotes are kept in memory for the job duration only. GitHub artifacts contain aggregate counts, source flags, and no betting recommendations.
- Snapshot hash and timestamp are verified; pair validation requires same book, player name, market, line, event, synchronized source time and fresh pregame capture. The provider does not supply an independently validated GSIS player ID, so the unique name match is a **proxy**. Out-of-date prices do not pass.
- Display only coverage: matched sides, paired markets, quote source timestamps, and aggregate projection-above/under-line counts and gap bands.
- A bookmaker quote may predate the forecast lock. We count those separately; do not pretend all available odds are post-lock quotes.

## Important limitations

Point projection minus quoted line is *not* a player-prop hit probability, expected value, value bet, or verified sportsbook edge. Source feeds still lack independently verified gameday actives, receiving routes, validated probability distributions for exactly the offered lines, and book-quote price-specific ROI evaluation. **Zero bets can qualify in Phase32**.

Future Phase33 should implement independent game-day active sources and calibrated probabilities per market threshold with uncertainty, including a robust historical future-as-of quote validation strategy, before a best-bets card is considered. Licensed line-level research output requires separate access controls; this repository must stay safe for public visibility.
