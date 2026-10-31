"""Leakage-safe current-slate predictions from completed regular-season games.

Only games before the as-of date train or inform forecasts. The historical
model is explicitly preliminary and does not incorporate current injuries.
"""
import pandas as pd
from .features import make_training_frame, FEATURES
from .predict import fit_baseline

SCHEDULE_REQUIRED = {"game_id","season","week","gameday","home_team","away_team","game_type","home_score","away_score"}

def upcoming_board(schedule, as_of, window=8, min_prior_games=4):
    missing=SCHEDULE_REQUIRED-set(schedule.columns)
    if missing:
        raise ValueError(f"Missing schedule columns: {sorted(missing)}")
    date=pd.Timestamp(as_of)
    data=schedule.copy()
    data["gameday"]=pd.to_datetime(data.gameday,errors="raise")
    regular=data.loc[data.game_type.eq("REG")].copy()
    past=regular.loc[(regular.gameday<date)&regular.home_score.notna()&
                     regular.away_score.notna()].copy()
    future=regular.loc[(regular.gameday>=date)&regular.home_score.isna()&
                       regular.away_score.isna()].sort_values(["gameday","game_id"]).copy()
    if future.empty:
        raise ValueError("No unplayed regular-season games on or after as-of date")
    training=make_training_frame(past,window=window,min_prior_games=min_prior_games)
    if len(training)<30 or training.home_win.nunique()<2:
        raise ValueError("Insufficient completed games for training")
    models=fit_baseline(training)
    # Construct latest available prior team form from the completed game history.
    home=past[["gameday","home_team","home_score","away_score"]].rename(
        columns={"home_team":"team","home_score":"points_for","away_score":"points_against"})
    away=past[["gameday","away_team","away_score","home_score"]].rename(
        columns={"away_team":"team","away_score":"points_for","home_score":"points_against"})
    long=pd.concat([home,away],ignore_index=True).sort_values("gameday")
    def latest(team, cutoff):
        games=long.loc[(long.team==team)&(long.gameday<cutoff)].tail(window)
        if len(games)<min_prior_games:
            return None
        return (float(games.points_for.mean()),float(games.points_against.mean()),len(games))
    rows=[]
    for _,g in future.iterrows():
        row={"game_id":g.game_id,"gameday":g.gameday,"season":g.season,
             "week":g.week,"home_team":g.home_team,"away_team":g.away_team}
        for side in ("home","away"):
            form=latest(g[f"{side}_team"],g.gameday)
            if form is None:
                break
            row.update({f"{side}_prior_for":form[0],
                        f"{side}_prior_against":form[1],
                        f"{side}_prior_games":form[2]})
        else:
            rows.append(row)
    if not rows:
        raise ValueError("No upcoming games have enough historical team form")
    frame=pd.DataFrame(rows)
    X=frame[FEATURES]
    frame["pred_margin"]=models["margin"].predict(X)
    frame["pred_total"]=models["total"].predict(X)
    frame["home_win_probability"]=models["winner"].predict_proba(X)[:,1]
    frame["away_win_probability"]=1-frame.home_win_probability
    frame["projected_home_points"]=(frame.pred_total+frame.pred_margin)/2
    frame["projected_away_points"]=(frame.pred_total-frame.pred_margin)/2
    frame["projected_winner"]=frame.apply(
        lambda r:r.home_team if r.home_win_probability>=0.5 else r.away_team,axis=1)
    frame["fair_home_spread"]=-frame.pred_margin
    frame["model_status"]="PRELIMINARY_BASELINE_NO_INJURY_OR_MARKET_ADJUSTMENT"
    return frame[["game_id","gameday","season","week","home_team","away_team",
        "projected_winner","home_win_probability","away_win_probability",
        "projected_home_points","projected_away_points","fair_home_spread",
        "pred_total","model_status"]]
