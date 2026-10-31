"""Construct pregame features. Scores are targets only, never model inputs."""
import pandas as pd
from .ratings import prior_team_form

FEATURES = ["home_prior_for","home_prior_against","away_prior_for","away_prior_against","home_prior_games","away_prior_games"]

def make_training_frame(games, window=8, min_prior_games=4):
    form = prior_team_form(games,window)
    out = games.copy()
    for side in ("home","away"):
        f = form.rename(columns={"team":f"{side}_team",
            "prior_points_for":f"{side}_prior_for",
            "prior_points_against":f"{side}_prior_against",
            "prior_games":f"{side}_prior_games"})
        out = out.merge(f,on=[f"{side}_team","gameday"],how="left",validate="many_to_one")
    out["margin"] = out.home_score - out.away_score
    out["total"] = out.home_score + out.away_score
    out["home_win"] = (out.margin > 0).astype(int)
    eligible = (out.home_prior_games >= min_prior_games) & (out.away_prior_games >= min_prior_games)
    return out.loc[eligible].dropna(subset=FEATURES).sort_values(["gameday","game_id"]).reset_index(drop=True)
