"""Leakage-aware, opponent-adjusted team EPA ratings.

Input is a nflverse play-by-play CSV with game_id, season, week, game_date,
posteam, defteam, play_type, and epa. Ratings are estimated from completed
games strictly BEFORE the target game's date. This is a deliberately simple
ridge-adjusted attack/defense model, not a coverage or personnel model.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

REQUIRED = {"game_id","game_date","posteam","defteam","play_type","epa"}

def aggregate_games(plays):
    missing = REQUIRED - set(plays.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    p = plays.loc[plays.play_type.isin(["pass","run"])].copy()
    p["game_date"] = pd.to_datetime(p.game_date, errors="raise")
    p["epa"] = pd.to_numeric(p.epa,errors="coerce")
    p = p.dropna(subset=["posteam","defteam","epa"])
    p = p.loc[p.posteam.ne(p.defteam)]
    return p.groupby(["game_id","game_date","posteam","defteam","play_type"],as_index=False).agg(
        epa_mean=("epa","mean"), plays=("epa","size"))

def adjusted_team_ratings(game_aggregates, as_of, alpha=20.0, min_games=4):
    """Fit ridge offense/defense effects on games strictly before as_of.

    A team's offensive rating is the contribution to EPA, and defensive
    rating is the EPA *allowed* contribution (lower is better).
    Identifiability is stabilized through ridge regularization.
    """
    cutoff = pd.Timestamp(as_of)
    history = game_aggregates.loc[game_aggregates.game_date < cutoff].copy()
    if history.empty:
        return pd.DataFrame(columns=["team","play_type","off_epa","def_epa_allowed","prior_games"])
    teams = sorted(set(history.posteam) | set(history.defteam))
    n = len(teams)
    team_index = {t:i for i,t in enumerate(teams)}
    rows=[]
    for play_type in ("pass","run"):
        sub=history.loc[history.play_type.eq(play_type)].copy()
        if sub.empty:
            continue
        X=np.zeros((len(sub),2*n))
        for j,(off,defn) in enumerate(zip(sub.posteam,sub.defteam)):
            X[j,team_index[off]]=1
            X[j,n+team_index[defn]]=1
        model=Ridge(alpha=alpha,fit_intercept=True).fit(
            X,sub.epa_mean,sample_weight=sub.plays)
        offense=model.coef_[:n]
        defense=model.coef_[n:]
        counts=pd.concat([
            sub[["game_id","posteam"]].rename(columns={"posteam":"team"}),
            sub[["game_id","defteam"]].rename(columns={"defteam":"team"})
        ]).groupby("team").game_id.nunique()
        for t in teams:
            games=int(counts.get(t,0))
            if games >= min_games:
                rows.append({"team":t,"play_type":play_type,
                    "off_epa":float(model.intercept_+offense[team_index[t]]),
                    "def_epa_allowed":float(model.intercept_+defense[team_index[t]]),
                    "prior_games":games})
    return pd.DataFrame(rows,columns=["team","play_type","off_epa","def_epa_allowed","prior_games"])
