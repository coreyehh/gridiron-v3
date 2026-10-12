# GRIDIRON 3.0 — PRIVATE PLAYER PROP DASHBOARD

**Status:** Dashboard code implemented. Runs on your Mac; you need the TWO encrypted files created by your successful Phase 19 live run. The GitHub repository is public. **Never put your archive secret, decrypted data, or plaintext individual sportsbook lines in this public repository.**

## Launch the dashboard on your Mac

**Step 1: Download the dashboard code.** Open https://github.com/coreyehh/gridiron-v3 and use **Code → Download ZIP**. Unzip and open the project folder.

**Step 2: Download your private player data.** Open the successful Phase 19 run: https://github.com/coreyehh/gridiron-v3/actions/runs/38320842317 . Scroll to **Artifacts** → download **phase19-encrypted-private-ledger**. Unzip it. It contains `phase19_forecasts.enc` and `phase19_private_comparison.enc`. Artifacts expire after 30 days.

**Step 3: Run the local dashboard.** Open **Terminal** on your Mac and type `cd ` (with a trailing space), then drag the unzipped `gridiron-v3-main` folder into the Terminal window and press Return.

Then run these commands, one by one:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install streamlit pandas cryptography
python -m streamlit run dashboard.py --server.address 127.0.0.1 --browser.gatherUsageStats false
```

Your browser will open a local dashboard, typically at http://127.0.0.1:8501 .

**Step 4: Unlock only inside your local dashboard.** In the left sidebar, upload the two `.enc` files from Step 2. Paste your saved **GRIDIRON_ARCHIVE_KEY** into the dashboard's password field. **Do not paste the key in ChatGPT.** The dashboard decrypts locally. It does not call The Odds API.

## What you can see

- Locked player-level receptions and receiving-yard point projections.
- A single row per matched player and market, with a range and **distinct-line median** across available sportsbooks. Repeated over/under quotes are not counted as extra player forecasts.
- Individual sportsbook quotes including bookmaker, over/under side, American odds, line, and projection-to-line gap.
- Separate quote timestamp clocks and filters for players, markets, books and quotes updated after the lock.
- Actual source snapshot identity and aggregate Phase 19 status when both encrypted archives are supplied.

## What the dashboard DOES NOT demonstrate

- No validated probabilities to beat the offered book line or proved expected value.
- No official game-day active or injury verification.
- No opponent coverage, run/pass strategy or verified usage adjustments.
- No official promoted bets and no verifiable ROI.
- Book prices and player forecasts remain **research-only**, and the Phase 19 run archived 30 days only.

## Safety and privacy

- Run the app **only on your own Mac**, bound to `127.0.0.1`, not a public hosting service.
- The encryption key must be the **same key that existed when Phase 19 created these artifacts**. If you rotate the GitHub secret later, you still need the older saved key to decrypt older artifacts.
- Do not deploy this app publicly, share a public dashboard link or commit the plaintext artifacts. Streamlit runs a local service and maintains the temporary decrypted dataset in local session memory.
- If you download the repo again for a new dashboard version, don't confuse it with the downloaded Phase 19 encrypted records; the data are not committed in GitHub.
- Official bets can be considered only after eligibility, injury/scheme context, probability distributions, actual sportsbook prices and prospective accountability are added.

## Optional GitHub offline verification

In Actions, run **GRIDIRON private dashboard offline checks**. It compiles the UI and tests encryption, SHA-256 pairing, duplicate quote deduplication and research-only tagging. This workflow does not use API credits or decrypt any private dataset.
