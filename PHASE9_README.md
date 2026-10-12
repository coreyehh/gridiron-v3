# GRIDIRON 3.0 — Phase 9 (participation proxy)

## What is real, and what is not

Verified NFLverse release `pbp_participation` has 2021–2025 Parquet files and records `offense_players` (who was on the field for a play). This **does not show which non-targeted RBs ran routes**. The `route` field denotes only the *primary receiver's route*, not all players' routes. **Never label on-field pass-play appearances as routes run or targets per route run.**

The 2021–2022 files derive from NFL NextGenStats. 2023–2025 files are **FTN Data via nflverse** and carry CC BY-SA 4.0 terms: retain attribution and review redistribution obligations before sharing derived materials.

## What the workflow tests

1. Download participation releases for 2021–2025 and audit every file's source/hash.
2. Join offensive on-field players to play-by-play passing attempts by `game_id` + `play_id`.
3. Count RB appearances on passing-attempt plays per week.
4. Derive prior-five-game on-field passing-play appearances and historical targets per on-field passing play; shift all features so no *current game* observation enters a forecast.
5. Hold out 2025; fit/tune on 2021–2024; compare prior Phase 8 features against Phase 9 features on the **same** 2025 sample.
6. Report MAE, RMSE, sample sizes, coverage and whether new indicators improve the existing model.

Source: https://github.com/nflverse/nflverse-data/releases/tag/pbp_participation and https://nflreadr.nflverse.com/articles/dictionary_participation.html

## No claimed betting results

- No historical bookmaker-offered player prop universe
- No timestamped sportsbook odds / break-even prices
- No calibrated over/under probability / certified ROI
- No complete historical pregame active/inactive roster
- No actual all-receiver route participation or route rate

These limitations prevent promoting any prop as +EV based solely on this stage.
