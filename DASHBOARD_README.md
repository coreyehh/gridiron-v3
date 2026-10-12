# GRIDIRON — Simple Mac dashboard

## The easy way

**You do not need to install Python packages or enter Terminal commands each time.**

1. Open [GRIDIRON on GitHub](https://github.com/coreyehh/gridiron-v3). Choose **Code → Download ZIP**. Download the **updated** repository again (an older ZIP will not have the new launcher). Double-click the downloaded ZIP to unzip it.
2. Open the `gridiron-v3-main` folder in Finder. Double-click **OPEN GRIDIRON.command**. The first time, it installs the dashboard and might take a few minutes. Your browser will open automatically at **http://127.0.0.1:8501**.
3. From [your successful Phase 19 Bills–Rams run](https://github.com/coreyehh/gridiron-v3/actions/runs/38320842317), download **phase19-encrypted-private-ledger** from the **Artifacts** section. Keep it as a ZIP (do not unzip).
4. Drag that ZIP into the dashboard's **Drop the phase19-encrypted-private-ledger ZIP here** field. Enter the **private encryption key** you saved in your password manager. Never send the key to GitHub issues or this chat.
5. Your table appears: one row per player and prop, **GRIDIRON projection, median sportsbook line, projection-to-line difference, books covered**. Filter by player or market. Expand **View every sportsbook line and price** for the original book/side/odds quotes.

### If the Mac blocks the launcher

Right-click (or Control-click) **OPEN GRIDIRON.command** → **Open**, then approve opening if offered. Only do this for the launcher you downloaded from your own repository. You can also open **System Settings → Privacy & Security** to review an opening warning. If Finder says the file is not executable, tell me the exact error rather than pasting more commands.

### If Terminal says `dashboard.py` does not exist

That means you previously ran the old command from your home directory `~`. Use the **new** launcher inside the downloaded `gridiron-v3-main` folder instead. You can close the old Terminal window.

### If you see `Address already in use`

Another dashboard instance is running. Use **http://127.0.0.1:8501** in your browser, or close the old instance before double-clicking the launcher again.

### Security and limitations

- Your encrypted files and encryption key stay on your Mac when you use the dashboard locally, bound to `127.0.0.1`; don't deploy or share a public dashboard link.
- The dashboard makes **no paid odds requests** and does not use API credits.
- The encrypted ledger may expire from GitHub Actions after **30 days**. Save a private copy. If you lose the encryption key, the archive cannot be opened.
- The data are **research-only**, not validated betting picks. Official actives, matchup context, real-line probability calibration and expected ROI are not yet integrated.
- The existing model forecasts and sportsbook quotes are preserved as originally locked by Phase 19; the dashboard does not modify them.
