"""Fetch public NFL schedule/results for historical matchup baseline.

Source: nflverse/nfldata games.csv. No credentials required.
Only completed regular-season games enter the training dataset.
"""
from pathlib import Path
import pandas as pd

SOURCE = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"

def fetch_completed_games(output="data/matchup/completed_games.csv", source=SOURCE, through_season=2025):
    games = pd.read_csv(source)
    required = {"game_id","season","week","gameday","home_team","away_team","home_score","away_score","game_type"}
    missing = required - set(games.columns)
    if missing:
        raise ValueError(f"Missing schedule columns: {sorted(missing)}")
    games = games.loc[
        (games.game_type == "REG") &
        (games.season <= through_season) &
        games.home_score.notna() & games.away_score.notna(),
        ["game_id","season","week","gameday","home_team","away_team","home_score","away_score"]
    ].copy()
    games["gameday"] = pd.to_datetime(games.gameday, errors="raise")
    games = games.sort_values(["gameday","game_id"])
    if games.game_id.duplicated().any() or games.empty:
        raise ValueError("Duplicate IDs or no completed games")
    output = Path(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    games.to_csv(output,index=False)
    return games
