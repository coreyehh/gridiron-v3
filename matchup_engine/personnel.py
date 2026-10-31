"""Explicit, auditable manual personnel adjustment overlay.

This overlay never silently guesses injuries or roster assignments.
Each adjustment requires a game ID, team, signed points adjustment,
source, timestamp, and reason. These are *scenario assumptions*, not
validated causal player values.
"""
import pandas as pd

REQUIRED={"game_id","team","points_adjustment","source","observed_at","reason"}

def apply_personnel_scenarios(board, adjustments, as_of):
    missing=REQUIRED-set(adjustments.columns)
    if missing:
        raise ValueError(f"Missing personnel fields: {sorted(missing)}")
    result=board.copy()
    result["personnel_home_adjustment"]=0.
    result["personnel_away_adjustment"]=0.
    result["personnel_status"]="NO_VERIFIED_PERSONNEL_OVERLAY"
    if adjustments.empty:
        return result
    updates=adjustments.copy()
    updates["observed_at"]=pd.to_datetime(updates.observed_at,utc=True,errors="raise")
    cutoff=pd.Timestamp(as_of)
    if cutoff.tzinfo is None:
        cutoff=cutoff.tz_localize("UTC")
    else:
        cutoff=cutoff.tz_convert("UTC")
    if updates.observed_at.gt(cutoff).any():
        raise ValueError("Personnel information is dated after as-of cutoff")
    if updates[list(REQUIRED-{"points_adjustment","observed_at"})].isna().any().any():
        raise ValueError("Personnel adjustments require complete provenance")
    updates["points_adjustment"]=pd.to_numeric(updates.points_adjustment,errors="raise")
    if updates.points_adjustment.isna().any() or (updates.points_adjustment.abs()>14).any():
        raise ValueError("Personnel point adjustment outside allowable scenario range")
    if updates.duplicated(["game_id","team"]).any():
        raise ValueError("Multiple adjustments for same game and team must be aggregated explicitly")
    for _,a in updates.iterrows():
        ix=result.index[result.game_id.eq(a.game_id)]
        if len(ix)!=1:
            raise ValueError(f"Unknown game ID: {a.game_id}")
        idx=ix[0]
        if a.team==result.at[idx,"home_team"]:
            side="home"
        elif a.team==result.at[idx,"away_team"]:
            side="away"
        else:
            raise ValueError(f"Team {a.team} does not participate in {a.game_id}")
        result.at[idx,f"personnel_{side}_adjustment"]=a.points_adjustment
        result.at[idx,"personnel_status"]="MANUAL_SCENARIO_NOT_BACKTESTED"
    result["scenario_home_points"]=result.projected_home_points+result.personnel_home_adjustment
    result["scenario_away_points"]=result.projected_away_points+result.personnel_away_adjustment
    result["scenario_total"]=result.scenario_home_points+result.scenario_away_points
    result["scenario_home_spread"]=result.scenario_away_points-result.scenario_home_points
    return result
