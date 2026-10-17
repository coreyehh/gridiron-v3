# Phase 37 — Integrated Game-Day Research and FanDuel Price Evidence

**Status:** implemented and ready for first GitHub run; no claim of validated profitable bets.

## One-click workflow

[Phase37 integrated FanDuel workflow](https://github.com/coreyehh/gridiron-v3/actions/workflows/phase37-gameday-integration.yml)

Use branch main, bankroll 1000, unit percent 1, prior position history checked, and **request_live_fanduel unchecked** for the first offline run (no API credits). Download the HTML dashboard artifact for all Week6 frozen fixtures, sorted by projection with per-player PASS reasons. The JSON includes each player's forecast, positional evidence, exclusion and blocking reasons.

If explicitly requested, set **request_live_fanduel=true**. The Odds API key stays in GitHub Secrets. The live stage checks upcoming events, selects *one* matching fixture, calls the FanDuel-only player markets and validates equal-player, equal-line, equal-book, pregame, fresh two-sided outcomes. Public artifacts contain **only aggregate** FanDuel match diagnostics; licensed player/line/price pairs are processed transiently and not exported. This event quote call may incur paid API credits.

## End-to-end status and limitations

- Frozen forecast integrity verified by Phase31 SHA256.
- Prior-week NFLverse position field filters identifiable non-skill players; unknown stays unverified. Prior-week position does not prove game-day participation.
- Real FanDuel market sides map by unique normalized player name within a single known fixture, **not verified league player IDs**. Name ambiguity is rejected.
- **No authenticated official NFL inactive feed integrated.** The Phase36 source-provenance checker alone does not fetch and authenticate statuses. We explicitly mark this as missing, not solved.
- **No real-offer calibrated probability** is defensible from Phase33's one scored calibration week. Any projected-over-line gap is research, never certified EV.
- **No FanDuel accepted SGP price/feed**, no validated 2-5 leg joint player outcome model. Single prices must NOT be multiplied to simulate accepted FanDuel combined payouts.
- Portfolio policy uses 1 unit = 1% of bankroll by default, but with incomplete evidence **zero units are assigned**. A dashboard never auto-bets.
- This phase produces a usable integrated **matchup research and evidence dashboard**, not a final bet slip. Quote originals are not durably archived in GitHub.
- The existing GitHub repository is publicly readable, so no individual bookmaker offers, credentials, or sensitive accounts are written to GitHub Actions artifacts or logs.

**Next necessary actual engineering:** securely stored permitted quote history, independently sourced official inactive records with source retrieval/identity checks, sufficient prospective real-line calibration, and independently priced and tested FanDuel parlay payouts. Do not silently bypass these requirements.
