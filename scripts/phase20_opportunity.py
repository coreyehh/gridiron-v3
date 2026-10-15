"""GRIDIRON Phase 20: opponent-aware opportunity forecasts, no sportsbook request.

Forecast team pass attempts and carries first; allocate observed targets and
receiving opportunity to players. Historical information cutoff: completed
regular-season weeks strictly before target week. All model outputs are
*unvalidated research estimates*, not offered odds or eligible bets.
"""
import argparse,json,hashlib
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
from scripts.ingest import download
from scripts.phase18 import fetch_schedule,completed_weeks
from scripts.phase15 import team_code

VERSION="phase20-opportunity-v1"
TEAM_FIELD_CANDIDATES=("recent_team","team")
REQUIRED={"season","week","player_id","position","attempts","carries","targets",
          "receptions","receiving_yards"}
def normalize(frame):
    df=frame.copy()
    if "season_type" in df.columns:df=df[df["season_type"]=="REG"].copy()
    field=next((x for x in TEAM_FIELD_CANDIDATES if x in df),None)
    if not field:raise ValueError("Missing nflverse team field (recent_team/team)")
    missing=REQUIRED-set(df.columns)
    if missing:raise ValueError("Missing source opportunity fields: "+str(sorted(missing)))
    df["team_code"]=df[field].map(team_code)
    if df["team_code"].isna().any() or df["team_code"].eq("").any():
        raise ValueError("Unrecognized team code")
    if df.duplicated(["season","week","player_id"]).any():
        raise ValueError("Duplicate player-week")
    for col in ("attempts","carries","targets","receptions","receiving_yards"):
        df[col]=pd.to_numeric(df[col],errors="coerce")
        if df[col].isna().any() or (df[col]<0).any():raise ValueError("Missing/negative "+col)
    return df

def team_games(frame):
    # Sum across every offense contributor; do not confuse total QB attempts with scoring.
    frame=normalize(frame)
    grouped=frame.groupby(["season","week","team_code"],as_index=False).agg(
        pass_attempts=("attempts","sum"),rush_attempts=("carries","sum"),
        player_targets=("targets","sum"))
    if grouped.empty:raise ValueError("No team opportunity samples")
    grouped["target_coverage"]=grouped["player_targets"]/grouped["pass_attempts"].replace(0,np.nan)
    if (grouped.target_coverage>1.20).any():
        raise ValueError("Player targets exceed plausible pass attempt share; inspect inputs")
    return grouped

def schedule_opponents(schedule,season,allowed):
    s=schedule[(schedule.season==season)&(schedule.week.isin(allowed))&
               (schedule.game_type=="REG")].copy()
    return {(int(r.week),str(r.home_team)):str(r.away_team) for r in s.itertuples()} | {
       (int(r.week),str(r.away_team)):str(r.home_team) for r in s.itertuples()}

def prior_mean(series,default):
    v=pd.to_numeric(series,errors="coerce").dropna().tail(5)
    return float(v.mean()) if len(v) else float(default)

def opportunity_forecast(games,schedule,team,opponent,allowed):
    team=team_code(team);opponent=team_code(opponent)
    if not allowed:raise ValueError("No completed 2026 weeks available")
    recent=games[(games.season==2026)&games.week.isin(allowed)].copy()
    old=games[(games.season==2025)].copy()
    if recent.empty:raise ValueError("No current-season team games")
    opponents=schedule_opponents(schedule,2026,allowed)
    # Opposing offense's pass/rush *faced* equals its opponent's attempts.
    def faced(defender,column):
        vals=[]
        for row in recent.itertuples():
            if opponents.get((int(row.week),row.team_code))==defender:
                vals.append(float(getattr(row,column)))
        return vals
    out={}
    for club,defender in ((team,opponent),(opponent,team)):
        own=recent[recent.team_code==club].sort_values("week")
        hist=old[old.team_code==club].sort_values("week")
        if own.empty or hist.empty:
            raise ValueError("Missing 2025 baseline or 2026 current form for "+club)
        out[club]={}
        for col in ("pass_attempts","rush_attempts"):
            recent_avg=prior_mean(own[col],0)
            baseline=prior_mean(hist[col],recent_avg)
            # Shrink 2026 sample toward last five 2025 games.
            n=min(len(own),6);shrink=n/(n+4)
            offense=shrink*recent_avg+(1-shrink)*baseline
            defense=faced(defender,col)
            # Avoid over-weighting <=2 samples of defense allowance.
            defense_weight=min(len(defense)/8,0.25)
            estimate=(1-defense_weight)*offense+defense_weight*(
                float(np.mean(defense)) if defense else offense)
            out[club][col]={"projection":round(max(0,estimate),2),
                "offense_recent_mean":round(recent_avg,2),
                "offense_2025_baseline":round(baseline,2),
                "defense_sample_games":len(defense),
                "offense_2026_sample_games":len(own),
                "method":"offense-prior-shrink-plus-weak-defense-exposure"}
    return out

def player_forecast(frame,team_projection,allowed,club,roster=None):
    club=team_code(club)
    f=normalize(frame)
    recent=f[(f.season==2026)&f.week.isin(allowed)&(f.team_code==club)].copy()
    baseline=f[(f.season==2025)&(f.team_code==club)].copy()
    if recent.empty:raise ValueError("No completed current form for "+club)
    team_attempts=float(team_projection["pass_attempts"]["projection"])
    tgames=team_games(recent).sort_values("week")
    # Distribution based on team attempts across recent games, not total game score.
    # A player's absence remains an unknown active-status risk.
    denominator=float(tgames.pass_attempts.sum())
    if denominator<=0:raise ValueError("No team pass-attempt denominator")
    output=[]
    for pid,g in recent.groupby("player_id"):
        # Limited to players observed at least once for the SAME team in 2026.
        g=g.sort_values("week").tail(5)
        if g.empty:continue
        b=baseline[baseline.player_id==pid].sort_values("week").tail(5)
        total_targets=float(g.targets.sum())
        share=total_targets/denominator
        if total_targets==0:continue
        # Per-target rates shrink toward prior team-specific 2025 samples if present.
        baseline_t=float(b.targets.sum()) if len(b) else 0
        baseline_rec=float(b.receptions.sum()) if len(b) else 0
        baseline_yd=float(b.receiving_yards.sum()) if len(b) else 0
        catches=float(g.receptions.sum())
        yards=float(g.receiving_yards.sum())
        catch_rate=(catches+baseline_rec*0.20+2.0*0.68)/(total_targets+baseline_t*0.20+2.0)
        ypt=(yards+baseline_yd*0.20+2.0*7.0)/(total_targets+baseline_t*0.20+2.0)
        targets=team_attempts*share
        output.append({"player_id":str(pid),"team":club,
          "position":str(g.iloc[-1].position),"observed_games":len(g),
          "targets_per_team_attempt":round(share,4),
          "targets_projection":round(targets,2),
          "receptions_projection":round(targets*catch_rate,2),
          "receiving_yards_projection":round(targets*ypt,2),
          "unverified_active":True,
          "notes":"Role/active uncertainty; no snap-route or coverage conditioning"})
    # The shares are computed across all current games; partial appearance reduces per-game share.
    return sorted(output,key=lambda x:x["targets_projection"],reverse=True)

def run(year,week,club1,club2,folder):
    if year!=2026:raise ValueError("Only 2026 currently supported")
    if not 2<=week<=18:raise ValueError("Need target regular-season week 2-18")
    sch,shash=fetch_schedule(folder)
    allowed=completed_weeks(sch,week,datetime.now(timezone.utc).isoformat(),year)
    # Fail closed if week gaps: cannot build 2026 predictions using unverified games.
    if not allowed or max(allowed)<week-1:raise ValueError("Previous regular-season week not completed")
    match=sch[(sch.season==year)&(sch.week==week)&(sch.game_type=="REG")&
      (((sch.home_team==club1)&(sch.away_team==club2))|
       ((sch.home_team==club2)&(sch.away_team==club1)))]
    if len(match)!=1:raise ValueError("Requested matchup not scheduled for target week")
    frames=[];digests={"schedule":shash}
    for yr in (2025,2026):
        f,meta=download(yr,folder)
        frames.append(f);digests[str(yr)]=meta["sha256"]
    history=pd.concat(frames,ignore_index=True)
    selected=history[(history.season==2025)|((history.season==2026)&history.week.isin(allowed))].copy()
    games=team_games(selected)
    projections=opportunity_forecast(games,sch,club1,club2,allowed)
    players=player_forecast(selected,projections[club1],allowed,club1)+player_forecast(selected,projections[club2],allowed,club2)
    return {"model_version":VERSION,"status":"unvalidated_opportunity_research",
       "matchup":f"{club1} vs {club2}","target_week":week,
       "completed_2026_weeks":sorted(allowed),"team_projection":projections,
       "player_projections":players,"data_hashes":digests,
       "official_actives_verified":False,"player_routes_included":False,
       "matchup_scheme_included":False,"odds_prices_included":False,
       "calibrated_probabilities":False,"qualified_bets":0}

def markdown(report):
    lines=["# GRIDIRON 3.0 — Opportunity Research","",
       f"**{report['matchup']} · Week {report['target_week']}**",
       "**Unvalidated model research. NOT sportsbook picks.**","",
       "## Team volume forecast","",
       "| Team | Pass attempts | Rush attempts |","|---|---:|---:|"]
    for team,vals in report["team_projection"].items():
        lines.append(f"| {team} | {vals['pass_attempts']['projection']:.1f} | {vals['rush_attempts']['projection']:.1f} |")
    lines+=["","## Player opportunity forecast","",
        "| Player ID | Team | Targets | Receptions | Rec yards | Role sample games |",
        "|---|---|---:|---:|---:|---:|"]
    for p in sorted(report["player_projections"],key=lambda r:r["targets_projection"],reverse=True)[:40]:
        lines.append(f"| {p['player_id']} | {p['team']} | {p['targets_projection']:.1f} | {p['receptions_projection']:.1f} | {p['receiving_yards_projection']:.1f} | {p['observed_games']} |")
    lines+=["","Model does **not** know confirmed actives, routes, OL or defensive coverage, sportsbook price or line probability. Player IDs are GSIS identifiers until a verified current roster name-join is attached.",""]
    return "\n".join(lines)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--week",type=int,required=True)
    p.add_argument("--team-a",required=True)
    p.add_argument("--team-b",required=True)
    p.add_argument("--output",default="output/phase20_opportunity.json")
    args=p.parse_args()
    a,b=team_code(args.team_a),team_code(args.team_b)
    folder=Path("private_data");folder.mkdir(exist_ok=True)
    report=run(2026,args.week,a,b,folder)
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2))
    msg=markdown(report);print(msg)
    if __import__("os").environ.get("GITHUB_STEP_SUMMARY"):
        with open(__import__("os").environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write(msg)
if __name__=="__main__":main()
