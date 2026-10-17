"""Phase 29: route-data readiness + target-density research challenger.

True 2026 routes cannot be inferred from offensive snaps. This module audits
availability separately and tests a conservative target-per-offensive-snap
density trend, with historical weeks strictly before prediction week.
"""
import argparse,json,os,urllib.error,urllib.request
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
from scripts.phase28_snap_participation import (
    download_snaps,conservative_join,prior_snap_factor)
from scripts.phase26_matchup_board import build as board26
from scripts.phase15 import acquire
from scripts.ingest import download
from scripts.phase18 import fetch_schedule,completed_weeks
from scripts.phase20_opportunity import normalize,team_games,opportunity_forecast
from scripts.phase23_role_model import role_forecast

VERSION="phase29-route-source-audit-and-target-density-v1"
PARTICIPATION_URL="https://github.com/nflverse/nflverse-data/releases/download/pbp_participation/pbp_participation_2026.parquet"
MIN_MATCHED=3
DENSITY_WEIGHT=.20

def probe_route_participation(url=PARTICIPATION_URL):
    """Availability only; do not treat player participation as routes without schema."""
    try:
        req=urllib.request.Request(url,method="HEAD",headers={"User-Agent":"GRIDIRON-v3/1.0"})
        with urllib.request.urlopen(req,timeout=30) as res:
            available=200<=res.status<300
            status=res.status
    except urllib.error.HTTPError as exc:
        available=False;status=exc.code
    except (urllib.error.URLError,TimeoutError):
        available=False;status=None
    return {"dataset":"2026 nflverse PBP participation","url":url,
        "http_status":status,"download_available":available,
        "route_counts_derived":False,
        "why_not_routes":"Participation lists play-level players, not confirmed route assignments; current season may be unavailable",
        "current_game_routes_verified":False}

def density_factor(stats,joined,club,pid,allowed):
    """Fixed bounded ratio recent T/snap versus earlier mean; not targets/route."""
    player=stats[(stats.season==2026)&(stats.week.isin(allowed))&
        (stats.team_code==club)&(stats.player_id==pid)][["week","targets"]]
    snaps=joined[(joined.season==2026)&(joined.week.isin(allowed))&
        (joined.team_code==club)&(joined.player_id==pid)][["week","offense_snaps"]]
    z=player.merge(snaps,on="week",validate="one_to_one").dropna()
    z=z[z.offense_snaps>0].sort_values("week").tail(5)
    n=len(z)
    if n<MIN_MATCHED:return 1.,n,None
    total=float(z.offense_snaps.sum())
    current=float(z.tail(2).offense_snaps.sum())
    if total<=0 or current<=0:return 1.,n,None
    long=float(z.targets.sum())/total
    recent=float(z.tail(2).targets.sum())/current
    if long<=0:return 1.,n,None
    ratio=float(np.clip(recent/long,.75,1.25))
    factor=1.+DENSITY_WEIGHT*(ratio-1.)
    return factor,n,{"target_per_offensive_snap_last2":round(recent,4),
      "target_per_offensive_snap_last5":round(long,4),
      "actual_routes_run_unknown":True}

def evaluate(history,schedule,joined,first=4,last=18):
    stats=normalize(history);games=team_games(stats)
    completed=set(completed_weeks(schedule,min(last+1,19),"2099-01-01T00:00:00Z",2026))
    rows=[];eligible=0
    for week in range(max(4,first),min(18,last)+1):
        if week not in completed or week-1 not in completed:continue
        allowed={w for w in completed if w<week}
        past=stats[(stats.season==2025)|((stats.season==2026)&stats.week.isin(allowed))]
        actual=stats[(stats.season==2026)&(stats.week==week)]
        fixtures=schedule[(schedule.season==2026)&(schedule.week==week)&(schedule.game_type=="REG")]
        for g in fixtures.itertuples():
            home,away=str(g.home_team),str(g.away_team)
            try:volume=opportunity_forecast(games,schedule,home,away,allowed)
            except ValueError:continue
            for club in (home,away):
                try:players=role_forecast(past,volume[club]["pass_attempts"]["projection"],allowed,club)
                except ValueError:continue
                lookup=actual[actual.team_code==club].set_index("player_id")
                for player in players:
                    pid=str(player["player_id"])
                    factor,n,_=density_factor(past,joined,club,pid,allowed)
                    if n>=MIN_MATCHED:eligible+=1
                    for metric in ("targets","receptions","receiving_yards"):
                        observed=float(lookup.loc[pid,metric]) if pid in lookup.index else 0.
                        base=float(player[metric])
                        rows.append({"week":week,"metric":metric,"actual":observed,
                                     "baseline":base,"candidate":base*factor,
                                     "has_density_history":n>=MIN_MATCHED})
    if not rows:raise ValueError("No eligible 2026 completed player-game comparisons")
    metrics=[]
    for metric in ("targets","receptions","receiving_yards"):
        all_rows=[r for r in rows if r["metric"]==metric]
        adequate=[r for r in all_rows if r["has_density_history"]]
        def mae(part,key):
            return round(float(np.mean([abs(r[key]-r["actual"]) for r in part])),4) if part else None
        metrics.append({"metric":metric,"player_games":len(all_rows),
          "all_baseline_mae":mae(all_rows,"baseline"),
          "all_candidate_mae":mae(all_rows,"candidate"),
          "adequate_history_games":len(adequate),
          "adequate_baseline_mae":mae(adequate,"baseline"),
          "adequate_candidate_mae":mae(adequate,"candidate")})
    return {"evaluated_weeks":sorted({x["week"] for x in rows}),
       "player_games":len(rows)//3,
       "with_adequate_density_history":eligible,
       "metrics":metrics,
       "all_three_improve":all(r["all_candidate_mae"]<r["all_baseline_mae"] for r in metrics),
       "route_count_evaluated":False,"promoted_to_production":False,
       "qualified_bets":0}

def report_board(history,schedule,roster,joined,a="",b="",week=0):
    board=board26(schedule,history,roster,a,b,week)
    stats=normalize(history)
    allowed=set(board["completed_weeks"])
    for p in board["player_forecasts"]:
        factor,n,details=density_factor(stats,joined,p["team"],str(p["player_id"]),allowed)
        p["prior_density_games"]=n
        p["target_per_offensive_snap"]=details
        p["density_challenger_factor"]=round(factor,4)
        p["phase29_receiving_yards"]=round(p["receiving_yards"]*factor,2)
        p["true_routes_run_known"]=False
        p["route_participation_verified"]=False
    board["version"]=VERSION
    board["phase29_promoted"]=False
    board["qualified_bets"]=0
    return board

def markdown(board,result,probe):
    g=board["game"]
    lines=["# GRIDIRON Phase 29 — Routes readiness & opportunity density","",
      f"**{g['away']} @ {g['home']} · Week {g['week']} · {g['gameday']}**","",
      f"**2026 participation download available:** {probe['download_available']} (HTTP {probe['http_status']})",
      "**True player routes run:** NOT VERIFIED. Target density is targets / offensive snaps, not targets / routes.","",
      f"**Completed weeks tested:** {result['evaluated_weeks']}; **player-games:** {result['player_games']}; **adequate prior density history:** {result['with_adequate_density_history']}.","",
      "## Prediction error — challenger vs. unchanged Phase 23 baseline","",
      "| Metric | Player-games | Baseline MAE | Density challenger MAE | Adequate history |",
      "|:--|--:|--:|--:|--:|"]
    for r in result["metrics"]:
        lines.append(f"| {r['metric']} | {r['player_games']} | {r['all_baseline_mae']:.3f} | {r['all_candidate_mae']:.3f} | {r['adequate_history_games']} |")
    lines+=["",f"**All 3 improve:** {result['all_three_improve']}. No automatic production promotion.","",
      "## Matchup players (illustrative challenger; no sportsbook odds)","",
      "| Player | Phase 23 yards | Phase 29 candidate yards | Prior snap-matched games |",
      "|:--|--:|--:|--:|"]
    for p in board["player_forecasts"][:18]:
        lines.append(f"| {p['player']} | {p['receiving_yards']:.1f} | {p['phase29_receiving_yards']:.1f} | {p['prior_density_games']} |")
    lines+=["","Historical offensive snap participation does not prove game-day active status, route rate, or targets per route run. No licensed odds or validated +EV predictions. **0 qualified bets.**",""]
    return "\n".join(lines)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--team-a",default="")
    p.add_argument("--team-b",default="")
    p.add_argument("--week",type=int,default=0)
    p.add_argument("--output",default="output/phase29_route_readiness.json")
    a=p.parse_args()
    folder=Path("private_data");folder.mkdir(exist_ok=True)
    schedule,schedule_hash=fetch_schedule(folder)
    frames=[];hashes={"schedule":schedule_hash}
    for season in (2025,2026):
        data,meta=download(season,folder);frames.append(data);hashes[str(season)]=meta["sha256"]
    history=pd.concat(frames,ignore_index=True)
    roster,rm=acquire(2026,folder);hashes["roster"]=rm["source_sha256"]
    snap,meta=download_snaps(2026,folder);hashes["offensive_snap"]=meta["sha256"]
    joined=conservative_join(history,snap,roster)
    probe=probe_route_participation()
    board=report_board(history,schedule,roster,joined,a.team_a,a.team_b,a.week)
    audit=evaluate(history,schedule,joined)
    board.update(phase29_audit=audit,route_source_probe=probe,source_hashes=hashes,
       routes_run_verified=False,game_day_actives_verified=False,qualified_bets=0)
    output=Path(a.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(board,indent=2))
    summary=markdown(board,audit,probe);print(summary)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write(summary)
if __name__=="__main__":main()
