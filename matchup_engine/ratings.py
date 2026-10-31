"""Leakage-safe, pregame team form using only completed earlier games."""
import pandas as pd

def prior_team_form(games, window=8):
    if window < 1:
        raise ValueError("window must be positive")
    g = games.sort_values(["gameday", "game_id"]).copy()
    home = g[["game_id","gameday","home_team","home_score","away_score"]].rename(
        columns={"home_team":"team","home_score":"points_for","away_score":"points_against"})
    away = g[["game_id","gameday","away_team","away_score","home_score"]].rename(
        columns={"away_team":"team","away_score":"points_for","home_score":"points_against"})
    long = pd.concat([home,away], ignore_index=True).sort_values(["gameday","game_id"])
    # Aggregate by date first so same-day games cannot inform one another.
    dates = long.groupby(["team","gameday"],as_index=False).agg(
        points_for=("points_for","mean"),points_against=("points_against","mean"))
    dates = dates.sort_values(["team","gameday"])
    for c in ("points_for","points_against"):
        dates["prior_"+c] = dates.groupby("team")[c].transform(
            lambda s: s.shift(1).rolling(window,min_periods=1).mean())
    dates["prior_games"] = dates.groupby("team").cumcount()
    return dates[["team","gameday","prior_points_for","prior_points_against","prior_games"]]
