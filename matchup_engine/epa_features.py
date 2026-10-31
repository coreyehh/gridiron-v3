"""Leakage-aware EPA feature generation with season-boundary cutoffs."""
import pandas as pd
from .epa_ratings import adjusted_team_ratings

EPA_FEATURES = [
    "home_pass_off_epa","home_pass_def_epa_allowed",
    "away_pass_off_epa","away_pass_def_epa_allowed",
    "home_run_off_epa","home_run_def_epa_allowed",
    "away_run_off_epa","away_run_def_epa_allowed",
]

def add_epa_features(frame, aggregates, min_games=4, alpha=20):
    """Attach ratings calculated only from games before each game date.

    A simple implementation optimized for correctness over speed: one fit
    per unique gameday. For full history, a later phase should cache fits.
    """
    pieces=[]
    for date, games in frame.groupby("gameday",sort=True):
        ratings=adjusted_team_ratings(aggregates,date,alpha=alpha,min_games=min_games)
        enriched=games.copy()
        for side in ("home","away"):
            for kind in ("pass","run"):
                subset=ratings.loc[ratings.play_type.eq(kind),
                    ["team","off_epa","def_epa_allowed"]].rename(columns={
                        "team":f"{side}_team",
                        "off_epa":f"{side}_{kind}_off_epa",
                        "def_epa_allowed":f"{side}_{kind}_def_epa_allowed"})
                enriched=enriched.merge(subset,on=f"{side}_team",how="left",validate="many_to_one")
        pieces.append(enriched)
    if not pieces:
        return frame.assign(**{col:pd.Series(dtype=float) for col in EPA_FEATURES})
    return pd.concat(pieces,ignore_index=True).sort_values(["gameday","game_id"]).reset_index(drop=True)
