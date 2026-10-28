"""Pregame opponent receiving context; descriptive, not an approved betting model.

Requires verified opponent_team on player-game rows. Historical opponent
allowance is shrunk toward same-position league averages to avoid overreacting
to weak schedules or tiny defensive samples.
"""
import math
import pandas as pd

POSITIONS=("WR","TE","RB")
MARKETS=("receptions","receiving_yards")

def opponent_context(history, *, opponent, position, season, week,
                     market="receiving_yards", shrink_games=40):
    if position not in POSITIONS or market not in MARKETS:
        raise ValueError("Unsupported position or receiving market")
    if not isinstance(shrink_games,int) or shrink_games<1:
        raise ValueError("Invalid shrinkage sample")
    required={"season","week","position","opponent_team",market}
    if not required.issubset(history.columns):
        raise ValueError("Verified opponent_team and player game fields required")
    if not isinstance(season,int) or not isinstance(week,int) or week<1 or week>18:
        raise ValueError("Invalid target game")
    prior=history[(history.season<season)|((history.season==season)&(history.week<week))]
    prior=prior[prior.position==position].copy()
    prior["_value"]=pd.to_numeric(prior[market],errors="coerce")
    prior=prior[prior["_value"].map(lambda v: pd.notna(v) and math.isfinite(float(v)) and
                               (market=="receiving_yards" or v>=0))]
    league=prior["_value"]
    facing=prior[prior.opponent_team==opponent]["_value"]
    if league.empty or facing.empty:
        return {"opponent":str(opponent),"position":position,"market":market,
                "sample_size":int(len(facing)),"league_mean":float(league.mean()) if len(league) else None,
                "opponent_mean":None,"shrunk_multiplier":None,
                "status":"INSUFFICIENT_PREGAME_OPPONENT_HISTORY","approved_wagers":0}
    baseline=float(league.mean())
    if baseline<=0:
        multiplier=None
    else:
        weight=len(facing)/(len(facing)+shrink_games)
        multiplier=round(max(0.5,min(1.5,1+weight*(float(facing.mean())/baseline-1))),6)
    return {"opponent":str(opponent),"position":position,"market":market,
            "sample_size":int(len(facing)),"league_mean":round(baseline,6),
            "opponent_mean":round(float(facing.mean()),6),
            "shrunk_multiplier":multiplier,
            "status":"DESCRIPTIVE_UNADJUSTED_FOR_OPPONENT_SCHEDULE_STRENGTH",
            "approved_wagers":0}
