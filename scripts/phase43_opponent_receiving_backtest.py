"""Paired chronological opponent adjustment test. Research-only; no wagering."""
import math
import pandas as pd
from scripts.phase43_opponent_receiving_context import opponent_context

def evaluate(raw, *, first_week=4,last_week=8,min_player_games=3,shrink_games=40):
    required={"season","week","player_id","position","opponent_team","receptions","receiving_yards"}
    if not required.issubset(raw.columns):
        raise ValueError("Player-week data with verified opponent_team required")
    if not 2<=first_week<=last_week<=18 or min_player_games<3:
        raise ValueError("Invalid chronological evaluation settings")
    data=raw.copy()
    if "season_type" in data:
        data=data[data.season_type=="REG"].copy()
    data=data[data.position.isin(("WR","TE","RB"))].copy()
    if data.duplicated(["season","week","player_id"]).any():
        raise ValueError("Duplicate player-week")
    data=data.sort_values(["season","week","player_id"])
    rows=[]
    for game in data[(data.season==2026)&data.week.between(first_week,last_week)].itertuples():
        if pd.isna(game.opponent_team) or pd.isna(game.player_id):
            continue
        prior=data[(data.season<game.season)|((data.season==game.season)&(data.week<game.week))]
        player=prior[prior.player_id==game.player_id].tail(5)
        if len(player)<min_player_games:continue
        for market in ("receptions","receiving_yards"):
            vals=pd.to_numeric(player[market],errors="coerce").dropna()
            if len(vals)<min_player_games:continue
            baseline=float(vals.mean())
            observed=float(getattr(game,market))
            if not math.isfinite(observed) or (market=="receptions" and observed<0):continue
            context=opponent_context(prior,opponent=game.opponent_team,position=game.position,
                 season=int(game.season),week=int(game.week),market=market,shrink_games=shrink_games)
            factor=context.get("opponent_strength_adjusted_multiplier")
            if factor is None:continue
            adjusted=baseline*factor
            rows.append({"week":int(game.week),"player_id":str(game.player_id),"market":market,
                "position":str(game.position),"opponent":str(game.opponent_team),
                "actual":observed,"baseline":baseline,"adjusted":adjusted,
                "baseline_absolute_error":abs(observed-baseline),
                "adjusted_absolute_error":abs(observed-adjusted),
                "context_sample":context["opponent_strength_adjusted_samples"]})
    metrics={}
    for market in ("receptions","receiving_yards"):
        subset=[r for r in rows if r["market"]==market]
        if not subset:
            metrics[market]={"n":0,"baseline_mae":None,"adjusted_mae":None,
                             "paired_mae_improvement":None}
            continue
        n=len(subset)
        baseline=sum(r["baseline_absolute_error"] for r in subset)/n
        adjusted=sum(r["adjusted_absolute_error"] for r in subset)/n
        metrics[market]={"n":n,"baseline_mae":round(baseline,6),
                         "adjusted_mae":round(adjusted,6),
                         "paired_mae_improvement":round(baseline-adjusted,6)}
    return {"status":"RESEARCH_ONLY","season":2026,"first_week":first_week,
            "last_week":last_week,"scored_rows":len(rows),"metrics":metrics,
            "sample_selection":"ONLY_PLAYER_GAMES_WITH_PRIOR_OPPONENT_CONTEXT",
            "limitations":["Observed player games only; DNP rows not imputed",
                           "No active or sportsbook verification",
                           "Schedule-adjusted allowance is a historical heuristic",
                           "No statistical significance established"],
            "approved_wagers":0}
