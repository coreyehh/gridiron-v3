"""Phase 28 — authentic prior-game offensive snap participation challenger.

PFR snap counts (via nflverse) have PFR IDs; player-week stats use GSIS IDs.
Use an EXACT unique normalized name + team + season/week crosswalk only.
Ambiguous, unmatched, and missing observations cannot be treated as zero snaps
or official game-day availability. All features must predate target week.
"""
import argparse,hashlib,json,os,re,shutil,unicodedata
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
import numpy as np
import pandas as pd
from scripts.ingest import download
from scripts.phase15 import acquire,team_code
from scripts.phase18 import fetch_schedule,completed_weeks
from scripts.phase20_opportunity import normalize,team_games,opportunity_forecast
from scripts.phase23_role_model import role_forecast
from scripts.phase26_matchup_board import build as board26

VERSION="phase28-authentic-offensive-snap-challenger-v1"
SNAP_URL="https://github.com/nflverse/nflverse-data/releases/download/snap_counts/snap_counts_{season}.parquet"
REQUIRED={"season","week","game_type","team","player","offense_snaps","offense_pct"}
MIN_PRIOR_MATCHED=2
STRENGTH=.35

def name_key(value):
    if not isinstance(value,str):return ""
    value=unicodedata.normalize("NFKD",value)
    value="".join(c for c in value if not unicodedata.combining(c))
    value=re.sub(r"[^a-z0-9 ]"," ",value.lower())
    value=re.sub(r"\b(jr|sr|ii|iii|iv)\b","",value)
    return " ".join(value.split())

def validate_snap_frame(frame,season):
    absent=REQUIRED-set(frame.columns)
    if absent:raise ValueError("Missing PFR snap source fields: "+str(sorted(absent)))
    v=frame[(frame.season==season)&(frame.game_type=="REG")].copy()
    if v.empty:raise ValueError("No regular season snap records")
    v["team_code"]=v.team.map(team_code)
    v["key"]=v.player.map(name_key)
    if v.team_code.isna().any() or v.key.eq("").any():raise ValueError("Invalid PFR team/name")
    for c in ("offense_pct","offense_snaps"):
        v[c]=pd.to_numeric(v[c],errors="coerce")
    if v[["offense_pct","offense_snaps"]].isna().any().any():raise ValueError("Null snap measurements")
    # PFR pct may use fraction [0,1] or percent [0,100].
    if v.offense_pct.max()>1.01:
        if v.offense_pct.max()>100.1:raise ValueError("Invalid snap percentage")
        v["offense_pct"]=v.offense_pct/100.
    if ((v.offense_pct<0)|(v.offense_pct>1.001)|(v.offense_snaps<0)).any():
        raise ValueError("Invalid snap proportion/count")
    if v.duplicated(["season","week","team_code","key"]).any():
        # Same normalized name on the same team is unresolved.
        raise ValueError("Ambiguous PFR player-week name")
    return v

def download_snaps(season,folder):
    url=SNAP_URL.format(season=season)
    dest=folder/f"snap_counts_{season}.parquet"
    with urlopen(Request(url,headers={"User-Agent":"GRIDIRON-v3-snap-evidence/1.0"}),timeout=120) as response, dest.open("wb") as f:
        shutil.copyfileobj(response,f)
    raw=pd.read_parquet(dest)
    return validate_snap_frame(raw,season),{"source":url,"sha256":hashlib.sha256(dest.read_bytes()).hexdigest(),
     "observations":len(raw),"season":season}

def conservative_join(stats,snaps,roster):
    """One-to-one, season/team/week/name join with stable roster identity evidence.

    Name+team matching is a proxy, not formal GSIS<->PFR crosswalk.
    """
    a=normalize(stats).copy()
    r=pd.DataFrame([{"player_id":str(x["player_id"]),"team_code":team_code(x["team"]),
         "key":name_key(x["player_name"])} for x in roster])
    if r.empty:raise ValueError("Empty roster crosswalk")
    r=r.drop_duplicates()
    # If one name maps to multiple GSIS IDs on the team, disallow it.
    bad=r.groupby(["team_code","key"]).player_id.nunique()
    ambiguous=set(bad[bad!=1].index)
    r=r[~r.apply(lambda x:(x.team_code,x.key) in ambiguous,axis=1)]
    ids=a[["season","week","team_code","player_id"]].merge(
      r,on=["team_code","player_id"],how="left",validate="many_to_one")
    duplicate=ids.groupby(["season","week","team_code","key"],dropna=True).player_id.nunique()
    bad_names=set(duplicate[duplicate>1].index)
    ids=ids[~ids.apply(lambda x:(x.season,x.week,x.team_code,x.key) in bad_names,axis=1)]
    joined=ids.merge(snaps[["season","week","team_code","key","offense_pct","offense_snaps"]],
      on=["season","week","team_code","key"],how="left",validate="many_to_one")
    return joined[["season","week","team_code","player_id","offense_pct","offense_snaps"]]

def prior_snap_factor(prior_join,club,pid,allowed):
    observations=prior_join[(prior_join.season==2026)&
      (prior_join.week.isin(allowed))&(prior_join.team_code==club)&
      (prior_join.player_id==pid)].dropna(subset=["offense_pct"]).sort_values("week")
    if len(observations)<MIN_PRIOR_MATCHED:return 1.,len(observations),None
    # Fixed before model evaluation. Avoid reacting strongly to two games.
    values=observations.offense_pct.astype(float)
    recent=float(values.tail(2).mean())
    mean=float(values.tail(5).mean())
    if mean<.1:return 1.,len(values),None
    raw=np.clip(recent/mean,.75,1.25)
    factor=1.+STRENGTH*(raw-1.)
    return float(factor),len(values),{"recent_offense_pct":round(recent,3),
       "five_offense_pct":round(mean,3)}

def evaluate(history,schedule,join,first=4,last=18):
    frame=normalize(history);all_games=team_games(frame)
    done=set(completed_weeks(schedule,min(19,last+1),"2099-01-01T00:00:00Z",2026))
    rows=[];match_counts=Counter()
    for week in range(max(4,first),min(last,18)+1):
        if week not in done or week-1 not in done:continue
        allowed={x for x in done if x<week}
        prior=frame[(frame.season==2025)|((frame.season==2026)&frame.week.isin(allowed))]
        actual=frame[(frame.season==2026)&(frame.week==week)]
        matches=schedule[(schedule.season==2026)&(schedule.week==week)&(schedule.game_type=="REG")]
        for match in matches.itertuples():
            a,b=str(match.home_team),str(match.away_team)
            try:volume=opportunity_forecast(all_games,schedule,a,b,allowed)
            except ValueError:continue
            for club in (a,b):
                try:forecasts=role_forecast(prior,volume[club]["pass_attempts"]["projection"],allowed,club)
                except ValueError:continue
                truth=actual[actual.team_code==club].set_index("player_id")
                for player in forecasts:
                    pid=str(player["player_id"])
                    factor,n,_=prior_snap_factor(join,club,pid,allowed)
                    match_counts["forecast_players"]+=1
                    if n>=MIN_PRIOR_MATCHED:match_counts["sufficient_prior_snap_history"]+=1
                    else:match_counts["insufficient_prior_snap_history"]+=1
                    if abs(factor-1)>1e-6:match_counts["nonneutral_adjustments"]+=1
                    for metric in ("targets","receptions","receiving_yards"):
                        actual_value=float(truth.loc[pid,metric]) if pid in truth.index else 0.
                        rows.append({"metric":metric,"week":week,"actual":actual_value,
                          "base":float(player[metric]),
                          "challenger":float(player[metric])*factor,
                          "sufficient_source":n>=MIN_PRIOR_MATCHED})
    if not rows:raise ValueError("No scored 2026 games available")
    comparisons=[]
    for metric in ("targets","receptions","receiving_yards"):
        market=[x for x in rows if x["metric"]==metric]
        def mae(x,k):return float(np.mean([abs(v[k]-v["actual"]) for v in x])) if x else None
        comparisons.append({"metric":metric,"n":len(market),
          "base_mae":round(mae(market,"base"),4),
          "challenger_mae":round(mae(market,"challenger"),4),
          "sufficient_snap_n":sum(x["sufficient_source"] for x in market),
          "sufficient_snap_base_mae":round(mae([x for x in market if x["sufficient_source"]],"base"),4) if any(x["sufficient_source"] for x in market) else None,
          "sufficient_snap_challenger_mae":round(mae([x for x in market if x["sufficient_source"]],"challenger"),4) if any(x["sufficient_source"] for x in market) else None})
    return {"weeks":sorted(set(r["week"] for r in rows)),"player_games":len(rows)//3,
       "join_diagnostics":dict(match_counts),"comparisons":comparisons,
       "all_metrics_improved":all(x["challenger_mae"]<x["base_mae"] for x in comparisons),
       "promotion_to_production":False,
       "same_week_snaps_used_for_prediction":False,
       "official_future_game_actives_verified":False,"routes_verified":False,
       "qualified_bets":0}

def build_live(history,schedule,roster,snaps,joined,team_a="",team_b="",week=0):
    base=board26(schedule,history,roster,team_a,team_b,week)
    allowed=set(base["completed_weeks"])
    verified_n=0
    for p in base["player_forecasts"]:
        factor,n,snapshot=prior_snap_factor(joined,p["team"],str(p["player_id"]),allowed)
        p["historical_snap_games_matched"]=n
        p["historical_snap_share"]=snapshot
        p["phase28_snap_challenger_factor"]=round(factor,4)
        p["phase28_challenger_targets"]=round(p["targets"]*factor,2)
        p["phase28_challenger_receptions"]=round(p["receptions"]*factor,2)
        p["phase28_challenger_receiving_yards"]=round(p["receiving_yards"]*factor,2)
        p["official_game_day_active_verified"]=False
        p["routes_verified"]=False
        if n>=MIN_PRIOR_MATCHED:verified_n+=1
    base.update(version=VERSION,qualified_bets=0,
      historical_snap_source="PFR offensive snaps supplied through nflverse",
      historical_snap_identity_match_method="unique roster name + team + season/week; NOT an authoritative PFR-GSIS crosswalk",
      player_forecasts_with_prior_snap_sample=verified_n,
      official_game_day_actives_verified=False,routes_verified=False,
      phase28_challenger_only=True)
    return base

def markdown(board,results,source):
    e=board["game"]
    lines=["# GRIDIRON Phase 28 — Authentic offensive snap participation","",
      f"**{e['away']} @ {e['home']} · Week {e['week']} · {e['gameday']}**",
      "**Prior-game offensive snap participation only; NOT routes, injuries, or verified future actives.**","",
      f"**Snap source:** {source['source']} (SHA-256 saved in JSON)", "",
      "## Matching diagnostic","",
      f"- Forecasted players with at least two matched prior snap games: {board['player_forecasts_with_prior_snap_sample']} / {len(board['player_forecasts'])}",
      f"- Backtest forecast player-games: {results['player_games']}",
      f"- Backtest players with sufficient prior snaps: {results['join_diagnostics'].get('sufficient_prior_snap_history',0)}","",
      "## Walk-forward receiving prediction error (lower better)","",
      "| Metric | Player-games | Phase 23 MAE | Snap challenger MAE | Matched-prior player-games |",
      "|:--|--:|--:|--:|--:|"]
    for x in results["comparisons"]:
        lines.append(f"| {x['metric']} | {x['n']} | {x['base_mae']:.3f} | {x['challenger_mae']:.3f} | {x['sufficient_snap_n']} |")
    lines+=["",f"All 3 historical metrics improved: **{results['all_metrics_improved']}**. Not promoted automatically.","",
       "## Prior offensive snaps — player example","",
       "| Player | Prior snap games | Phase23 receiving yards | Phase28 challenger yards |",
       "|:--|--:|--:|--:|"]
    for p in board["player_forecasts"][:18]:
        lines.append(f"| {p['player']} | {p['historical_snap_games_matched']} | {p['receiving_yards']:.1f} | {p['phase28_challenger_receiving_yards']:.1f} |")
    lines+=["","**Evidence gate:** a retrospective PFR snap observation is not an official gameday-active report. Absence of a snap record is not proof of inactivity. Crosswalk is not official ID mapping. Routes and bookmaker-line probabilities remain unverified. **0 qualified bets.**",""]
    return "\n".join(lines)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--team-a",default="")
    p.add_argument("--team-b",default="")
    p.add_argument("--week",type=int,default=0)
    p.add_argument("--output",default="output/phase28_snap_participation.json")
    a=p.parse_args()
    folder=Path("private_data");folder.mkdir(exist_ok=True)
    schedule,sha=fetch_schedule(folder)
    frames=[];hashes={"schedule":sha}
    for yr in (2025,2026):
        f,m=download(yr,folder);frames.append(f);hashes[str(yr)]=m["sha256"]
    history=pd.concat(frames,ignore_index=True)
    roster,roster_meta=acquire(2026,folder)
    hashes["roster"]=roster_meta["source_sha256"]
    snaps,source=download_snaps(2026,folder);hashes["snaps"]=source["sha256"]
    joined=conservative_join(history,snaps,roster)
    board=build_live(history,schedule,roster,snaps,joined,a.team_a,a.team_b,a.week)
    evaluation=evaluate(history,schedule,joined)
    board["snap_challenger_audit"]=evaluation
    board["source_sha256"]=hashes
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(board,indent=2))
    summary=markdown(board,evaluation,source);print(summary)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write(summary)
if __name__=="__main__":main()
