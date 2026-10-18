# GRIDIRON Phase 41 — unified Week 6 board and future-only market capture

Run [Phase41 GitHub Actions](https://github.com/coreyehh/gridiron-v3/actions/workflows/phase41-full-slate.yml).

**Recommended first run (free):** branch `main`, leave `collect_future_game_quotes=false`, `max_new_events=0`, historical `previous_ledger_run_id=39061690969`. Run workflow. Download the `phase41-READABLE-public-research-board` artifact, unzip, open HTML file with Chrome. The board contains all **294 frozen snapshot forecasts across 13 Week6 scheduled fixtures**, marked RESEARCH ONLY. It does NOT contain FanDuel prices.

Download `phase41-ENCRYPTED-all-captured-fanduel-markets`, unzip and load `locked_full_slate.fernet` using your **original QUOTE_ARCHIVE_KEY** in the pre-existing offline GRIDIRON private viewer. The private combined file includes the original 26 HOU-JAX markets; its schema retains Phase40 `entries` for current viewers.

**Optional paid capture for remaining unstarted games:** trigger Phase41 a second time with `collect_future_game_quotes=true` and choose a **nonzero** `max_new_events` (1,3,6,13). The script discovers future bookmaker events, matches only fixtures in the original frozen snapshot, skips the already-captured HOU-JAX fixture, and performs at most that number of additional per-event player-prop odds requests. The Odds API may charge credits per event/market. Games already kicked off cannot be captured retrospectively; no artificial historical odds are created. If a game starts between discovery and capture it is skipped. Available events may be fewer than selected cap.

**Privacy:** Public artifacts reveal frozen forecasts and whether a fixture has ANY encrypted capture; no individual sportsbook odds, lines, or pair rankings. Exact player-specific FanDuel markets appear only in the encrypted `locked_full_slate.fernet` opened locally with the key. Never commit plaintext odds or GitHub secrets.

**Research validity:** Differences between forecast and line are NOT calibrated betting probabilities. No verified individual game-day actives, accepted FanDuel SGP quote, approved picks or ROI claimed. Model forecasts may include bad roster/position assumptions; they remain immutable evidence, not wager eligibility. The full-slate combined archive is a browsing/evidence container, not a postgame-ready single-event Phase40 settlement ledger. For grading each fixture use individual archives and independently confirmed final score and player-week observations. Preserve originals and download artifacts within 30 days.

**Unresolved product limitation:** GitHub Actions upload artifacts are encrypted blobs and do not itself host an authenticated interactive dashboard. Use public standalone HTML for immediate no-key forecasts, and local private viewer for captured prices.
