# GRIDIRON Phase 39 — Official inactive-page observation & encrypted FanDuel quote evidence

## Run offline first

[Phase39 one-click workflow](https://github.com/coreyehh/gridiron-v3/actions/workflows/phase39-secure-quote-evidence.yml). Choose main, leave official probe ON and **archive_one_live_fanduel_event OFF**. No sportsbook credits used. It runs 13 new tests plus all earlier regression tests, and uploads the official page observation artifact.

## Official NFL inactives: what is and isn't implemented

The public [NFL Inactives](https://www.nfl.com/inactives/) page currently displays a message to check back for inactive reports. This code retrieves the genuine page over TLS, checks the exact approved origin, hashes raw bytes, strips scripts/styles for diagnostic visible-text extraction and detects unavailable/not-yet-posted reports. **It does NOT pretend the page lists GSIS IDs or imply a player is active when absent**. The official player-by-player list, game-specific identity and publication-time validation remain to be implemented when a reliable NFL feed supports it.

## Actual private FanDuel archive option

Public repos are readable, as are Actions artifacts to repo readers. **Never store plaintext quote prices, API tokens, or archive encryption keys in public logs or artifacts.** This phase creates a real encrypted evidence snapshot of normalized FanDuel quotes *within the live GitHub runner*, using the existing `cryptography` dependency: Fernet authenticated encryption (AES-128-CBC with HMAC-SHA256). Only **ciphertext** and a harmless aggregate JSON summary may enter Actions artifacts. The encrypted bundle includes the actual event context, line-specific FanDuel prices, timestamps, snapshot digest and valid quote rows, and can be decrypted off GitHub using the secret key.

To enable live one-game capture **you must first create a separate GitHub Actions repository secret named `QUOTE_ARCHIVE_KEY`**. On your own device generate a key using `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` (cryptography required), keep it securely backed up in a password manager, and enter it at Repository Settings → Secrets and variables → Actions → New repository secret. Never paste it into chat or a GitHub issue. This is separate from `ODDS_API_KEY`, which must also be valid.

Once the secret exists, check `archive_one_live_fanduel_event=true` and run on main. The workflow explicitly requests only one upcoming frozen fixture with `bookmakers=fanduel` and may consume Odds API credits; it must have a remaining eligible future fixture. It first checks the encryption key and fails before spending credits if absent. It writes a `fanduel_archive.fernet` ciphertext file and uploads it as an artifact, retained for **30 days**, plus a summary without player lines. Download and save the encrypted artifact elsewhere before it expires, since GitHub Artifacts are temporary and **not a durable archival service**.

To decrypt locally, use the module's `decrypt_archive(ciphertext, key)` on a trusted private computer; do not run decryption in a public Actions workflow or commit plaintext to the public repository. Anyone with access to the key and ciphertext can read the prices. Rotate a compromised key and capture new archives; key loss makes old archives irrecoverable.

## Strict limitations

This is a **real encrypted quote retention feature**, not player eligibility or a validated betting strategy. The Odds API does not bind normalized player props to authoritative NFL GSIS IDs; matched names are not verified identity. NFL page text is not authenticated individual game-day status. The 2026 Phase33/38 calibration audit has only one independently scored test week and no authenticated prior-book-offer archive; no FanDuel +EV selections can responsibly be promoted.

Official singles, 2–5-leg parlays, and units remain at **zero**, pending source-bound active/route evidence, prospective real-line calibration, verified book prices, and accepted FanDuel SGP payout evidence. No bets are placed.
