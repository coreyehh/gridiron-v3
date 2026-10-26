"""Audit identity/team mapping in source player-week boxes; not an active-roster feed."""
import argparse,json
from pathlib import Path
import pandas as pd

def audit(frame,season):
    required={"season","week","player_id","position"}
    missing=required-set(frame.columns)
    if missing:raise ValueError("Missing identity fields: "+str(sorted(missing)))
    team_col="recent_team" if "recent_team" in frame.columns else "team" if "team" in frame.columns else None
    if team_col is None:raise ValueError("Missing both recent_team and team columns")
    current=frame[frame.season==season].copy()
    if current.empty:raise ValueError("No rows for season")
    pid=current.player_id.astype("string").str.strip()
    team=current[team_col].astype("string").str.strip()
    identified=pid.notna()&pid.ne("")
    valid_team=team.notna()&team.str.fullmatch("[A-Z]{2,3}").fillna(False)
    missing_team=int((identified&~valid_team).sum())
    if missing_team:raise ValueError(f"{missing_team} identified player-week rows lack valid team code")
    good=current.loc[identified].copy()
    collisions=good.groupby(["season","week","player_id"])[team_col].nunique()
    conflicts=int((collisions>1).sum())
    if conflicts:raise ValueError(f"{conflicts} player-week IDs conflict across teams")
    missing_pos=int(good.position.isna().sum())
    if missing_pos:raise ValueError(f"{missing_pos} identified rows lack position")
    return {"status":"HISTORICAL_TEAM_IDENTITY_AUDITED_NOT_ACTIVE_VERIFIED",
        "season":season,"raw_rows":len(current),
        "identified_rows":len(good),"unidentified_rows_quarantined":int((~identified).sum()),
        "teams_observed":sorted(good[team_col].dropna().unique().tolist()),
        "team_count":int(good[team_col].nunique()),
        "latest_observed_week":int(good.week.max()),
        "conflicting_player_week_team_assignments":conflicts,
        "official_active_verified":False,"current_roster_verified":False,
        "expected_starter_verified":False,"approved_bets":0}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True)
    p.add_argument("--season",type=int,required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    result=audit(pd.read_parquet(a.source),a.season)
    path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=="__main__":main()
