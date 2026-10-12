# GRIDIRON 3.0 — Phase 19: exact matchup + durable encrypted locked forecasts

This stage addresses the Phase 18 result where all 199 retrieved sportsbook outcomes were rejected because bookmaker `last_update` preceded the forecast lock. It also fixes blind next-game selection and ephemeral forecast storage.

## New behavior

1. **Explicit matchup:** User sets two team codes (defaults `BUF` and `LA`, meaning Buffalo and the Los Angeles Rams). Discover the full API event list for free, require one unique **future** event involving both teams, or stop before consuming paid odds credits. Optional `kickoff_date` is the **UTC date**. The workflow does not silently substitute another opponent/game. A mismatch or an already-played Bills–Rams game must be reported as unavailable.
2. **Current form:** Download nflverse 2021–2026 player stats, 2026 roster IDs and schedule; call Phase 18 to generate 2026 completed-week-only player projections. This still omits official actives, injuries, route share, verified opponent coverage and offensive line context.
3. **Forecast lock before odds:** Seal the player-level predictions, source provenance, model version, target matchup and timestamp in `phase19_forecasts.enc` using Fernet authenticated symmetric encryption; record SHA-256 of the authenticated plaintext. **Only then** request paid bookmaker lines.
4. **Two valid clocks:** All quotes captured *after* the lock and *before* kickoff may be analyzed as **observed-after-lock** prices, even when unchanged since before the lock. Separately report the subset with the provider's own `quoted_at_utc` later than the lock as **updated-after-lock** prices. Never label the two categories interchangeably.
5. **Private usable records:** Encrypt the player-level comparison in `phase19_private_comparison.enc` with lines, book names, odds, model points, and both time classifications. Publish only anonymous aggregate results + two encrypted files (in an Actions artifact with **30-day retention**).
6. **No auto bets:** Model `model_probability=null`, `expected_roi=null`, `decision=INSUFFICIENT_DATA`, `qualified_bets=0`; no claim of bookmaker outperformance, independently verified official inactives, or ROI.

## One-time critical secret setup

The repository is **PUBLIC**. Never commit a secret, unencrypted forecast, raw odds file, or decrypted board. Before any live run, create a long random Fernet key on **your own computer**, for example:

```bash
python3 -m pip install 'cryptography>=43,<48'
python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

Save that key securely in a password manager. In GitHub → repository → Settings → Secrets and variables → Actions → **New repository secret**, add **`GRIDIRON_ARCHIVE_KEY`** with that value. Keep existing **`ODDS_API_KEY`** in Actions secrets. **Do not paste either key in ChatGPT or print them in workflow logs.** If you lose the archive key, encrypted files cannot be recovered; rotate it deliberately for future archives.

Without this second secret, the live step explicitly fails **before** any NFL prop-market request.

## Workflow

GitHub Actions → **GRIDIRON Phase 19 matchup-locked private board** → Run workflow on `main`.

- **First:** leave `use_api_credits` unchecked. Runs Phase 19 and Phase 18 tests and CLI smoke validation without touching The Odds API or the archive secret.
- **Then, only after tests pass and the archive key exists:** check `use_api_credits`, set `team_a=BUF`, `team_b=LA` and region `us` (or substitute the correct matchup). Optional `kickoff_date` must be a UTC date and can be left blank. If the provider has no future Bills–Rams event, the run should fail closed, not use another game.
- Successful live run uploads `phase19-aggregate-audit` (non-player-level) and `phase19-encrypted-private-ledger` (two .enc files), both retained **30 days**. Download these before they expire.

## Decrypt your own downloaded artifact locally

Extract `phase19-encrypted-private-ledger` to a **private** local folder and set `GRIDIRON_ARCHIVE_KEY` in your terminal session without posting it anywhere. From a local checkout with Python requirements installed:

```bash
python -m scripts.phase19 --decrypt private_data/phase19_private_comparison.enc --decrypt-output private_data/review_private.json
```

This reads your local key and writes plaintext privately on your computer; never commit that file, upload it to a public repository, or forward licensed sportsbook feeds without permission. The lock file can similarly be decrypted. GitHub Actions artifacts are retained for 30 days, **not indefinitely**, and the encryption key lives only in your GitHub secret and your own backup.

## Trust boundaries and next tasks

This is a reproducible **forecast-before-market-request** archive, not an independently attested timestamp. GitHub run history plus the hash provides audit context, but the encrypted blob's internal lock time is not a third-party timestamp service. Odds book `last_update` is not necessarily a first-publication timestamp; it indicates an update time supplied by the provider.

The roster is only an identity source; a player may be inactive. Phase 18's point forecasts remain simple recent-form regressions with no matchup scheme/OL/coverage/injury conditioning. Quote-vs-projection direction is not the chance of winning. Before any automatic official bets, integrate game-specific availability, point-in-time matchup features, calibrated probabilities on actual lines, price/EV gates, and a locked prospective accountability ledger.
