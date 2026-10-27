"""GRIDIRON Phase43 — independent pass, rush and TD baseline forecasting.

No bookmaker prices are inputs. Walk-forward samples and future-only locks;
any TD 2+/3+ Poisson tails are exploratory, NOT calibrated bet probabilities.
"""
import argparse,hashlib,json,math,os
from pathlib import Path
from datetime import datetime,timezone
import pandas as pd
from scripts.phase18 import fetch_schedule,completed_weeks
from scripts.ingest import download
from scripts.phase15 import acquire,team_code
from scripts.phase31_accountability import canonical,digest,validate_identity

VERSION="phase43-multi-market-player-baselines-v1"
STAT_MAP={
 "passing_yards":"passing_yards",
 "pass_attempts":"attempts",
 "completions":"completions",
 "interceptions":"interceptions",
 "passing_touchdowns":"passing_tds",
 "rushing_yards":"rushing_yards",
 "rush_attempts":"carries",
 "rushing_touchdowns":"rushing_tds",
 "receiving_touchdowns":"receiving_tds"}
REQUIRED={"season","week","player_id","position","passing_yards","attempts",
 "completions","interceptions","passing_tds","rushing_yards","carries",
 "rushing_tds","receiving_tds"}
MAE_METRICS=("passing_yards","pass_attempts","completions","interceptions",
             "passing_touchdowns","rushing_yards","rush_attempts",
             "anytime_touchdown","two_plus_touchdowns","three_plus_touchdowns")

def prep(frame):
    # nflverse stats_player_week calls this passing_interceptions in current
    # releases; support historic/synthetic interceptions without guessing.
    if "interceptions" not in frame.columns and "passing_interceptions" in frame.columns:
        frame=frame.rename(columns={"passing_interceptions":"interceptions"})
    if not REQUIRED.issubset(frame.columns):
        raise ValueError("Missing nflverse player statistics: "+str(sorted(REQUIRED-set(frame.columns))))
    f=frame.copy()
    # Quarantine unidentified player-week rows before any player grouping.
    identified=f["player_id"].notna() & f["player_id"].astype("string").str.strip().fillna("").ne("")
    f=f.loc[identified].copy()
    if f.empty:raise ValueError("No identified player-week records")
    if "season_type" in f:f=f[f.season_type=="REG"].copy()
    col="recent_team" if "recent_team" in f else "team"
    if col not in f:raise ValueError("Team code missing")
    f["team_code"]=f[col].map(team_code)
    if f.team_code.isna().any():raise ValueError("Unknown team")
    if f.duplicated(["season","week","player_id"]).any():raise ValueError("Duplicate player-week")
    for c in STAT_MAP.values():
        f[c]=pd.to_numeric(f[c],errors="coerce")
    f["total_scoring_tds"]=f["rushing_tds"]+f["receiving_tds"]
    return f

def tails(lam):
    """Poisson heuristic, uncalibrated (not a true TD concentration model)."""
    if not isinstance(lam,(int,float)) or not math.isfinite(lam) or lam<0:
        raise ValueError("Invalid TD intensity")
    zero=math.exp(-lam)
    one=zero*lam
    two=one*lam/2
    return {"anytime_touchdown":round(1-zero,6),
      "two_plus_touchdowns":round(max(0,1-zero-one),6),
      "three_plus_touchdowns":round(max(0,1-zero-one-two),6)}

def forecast_player(prior,position):
    """Only observed boxes. Never treat missing game rows as known zeros."""
    prior=prior.sort_values(["season","week"])
    if len(prior)<3:return None
    recent=prior.tail(5)
    past=prior[prior.season<2026].tail(5)
    if past.empty:past=prior.head(min(5,len(prior)))
    n=len(recent)
    weight=n/(n+5)
    out={}
    for label,col in STAT_MAP.items():
        x=recent[col].dropna();y=past[col].dropna()
        if len(x)<3 or len(y)<2:
            out[label]=None;continue
        mean=max(0,weight*float(x.mean())+(1-weight)*float(y.mean()))
        out[label]=round(mean,4)
    a=recent["total_scoring_tds"].dropna()
    b=past["total_scoring_tds"].dropna()
    lam=round(max(0,weight*float(a.mean())+(1-weight)*float(b.mean())),5) if len(a)>=3 and len(b)>=2 else None
    if lam is None:
        probs={"anytime_touchdown":None,"two_plus_touchdowns":None,"three_plus_touchdowns":None}
    else:probs=tails(lam)
    out.update({"td_count_mean":lam,**probs})
    return {"position":str(position),"observed_player_games":int(len(prior)),
      "last_observed_season":int(prior.iloc[-1].season),
      "last_observed_week":int(prior.iloc[-1].week),
      "point_projections":out,
      "source":"nflverse_observed_player_week",
      "touchdown_distribution":"UNCALIBRATED_POISSON_EXPLORATORY",
      "active_verified":False,"role_verified":False,
      "model_real_line_calibrated":False,"qualified_bet":False,
      "eligibility_status":"UNVERIFIED_GAME_DAY_ACTIVE_AND_ROLE",
      "eligible_for_wager_approval":False}

def build(schedule,raw,roster,week,asof,hashes):
    if asof.tzinfo is None:raise ValueError("UTC aware lock time required")
    asof=asof.astimezone(timezone.utc)
    if not 4<=week<=18:raise ValueError("Unknown week")
    allowed=completed_weeks(schedule,week,asof.isoformat(),2026)
    if max(allowed,default=0)!=week-1:raise ValueError("Previous week not fully complete")
    games=schedule[(schedule.season==2026)&(schedule.game_type=="REG")&
       (schedule.week==week)&(schedule.gameday.astype(str)>asof.date().isoformat())&
       (schedule.home_score.isna())&(schedule.away_score.isna())]
    if games.empty:raise ValueError("No strictly future unplayed fixtures")
    hist=prep(raw)
    prior=hist[(hist.season==2025)|((hist.season==2026)&hist.week.isin(allowed))].copy()
    if len(prior[(prior.season==2026)&(prior.week>=week)]):
        raise ValueError("Target-week outcome leak")
    roster_names=validate_identity(roster)
    roster_position={(str(r["team"]),str(r["player_id"])):str(r.get("position",""))
                     for r in roster}
    fixtures=[];forecasts=[]
    for g in games.sort_values(["gameday","home_team"]).itertuples():
        fid=f"2026-W{week:02d}-{g.away_team}-at-{g.home_team}"
        fixtures.append({"id":fid,"home":g.home_team,"away":g.away_team,"gameday":str(g.gameday)})
        for club in (g.away_team,g.home_team):
            names=sorted((pid,name) for (team,pid),name in roster_names.items() if team==club)
            for pid,name in names:
                observed=prior[(prior.player_id.astype(str)==pid)&(prior.team_code==club)]
                if observed.empty:continue
                position=roster_position[(club,pid)] or str(observed.iloc[-1].position)
                if position not in ("QB","RB","WR","TE"):continue
                info=forecast_player(observed,position)
                if info is None:continue
                forecasts.append({"fixture_id":fid,"team":club,"player_id":pid,
                  "player_name":name,**info})
    if not forecasts:raise ValueError("No source-backed player history for future games")
    obj={"version":VERSION,"season":2026,"week":week,
      "created_at_utc":asof.isoformat(),"prior_completed_weeks":sorted(allowed),
      "source_sha256":hashes,"fixtures":fixtures,"forecasts":forecasts,
      "model":"historical_obs_shrunk_mean_and_uncalibrated_td_poisson",
      "uses_bookmaker_odds":False,"qualified_bets":0,
      "game_day_active_verified":False,
      "td_2plus_3plus_probabilities_validated":False,
      "past_fixture_forecasts_reconstructed":False}
    obj["payload_sha256"]=digest(obj)
    return obj

def verify(obj):
    if obj.get("version")!=VERSION:raise ValueError("Invalid Phase43 version")
    copy=dict(obj);x=copy.pop("payload_sha256",None)
    if not x or digest(copy)!=x:raise ValueError("Invalid forecast lock digest")
    lock=pd.Timestamp(obj["created_at_utc"])
    if lock.tzinfo is None:raise ValueError("No forecast lock timezone")
    for f in obj["fixtures"]:
        if f["gameday"]<=lock.date().isoformat():raise ValueError("Nonfuture forecast fixture")
    names=set()
    for r in obj["forecasts"]:
        key=(r["fixture_id"],r["team"],r["player_id"])
        if key in names:raise ValueError("Duplicate forecast")
        names.add(key)
        values=r["point_projections"]
        if r["fixture_id"] not in {f["id"] for f in obj["fixtures"]}:
            raise ValueError("Unknown fixture")
        for k,v in values.items():
            if v is not None and (not isinstance(v,(float,int)) or not math.isfinite(v) or v<0):
                raise ValueError("Invalid projection")
    return True

def walk_forward(raw,first=4,last=6):
    """Observed-row-only 2026 backtest. Avoid converting absent rows to zero.

    Training includes last season and earlier current-season observed boxes.
    This is NOT an independent line-specific calibration report.
    """
    h=prep(raw)
    records=[]
    for wk in range(first,last+1):
        prior=h[(h.season==2025)|((h.season==2026)&(h.week<wk))]
        actual=h[(h.season==2026)&(h.week==wk)]
        for r in actual.itertuples():
            past=prior[(prior.player_id==r.player_id)&(prior.team_code==r.team_code)]
            fc=forecast_player(past,r.position)
            if fc is None:continue
            for label,col in STAT_MAP.items():
                v=fc["point_projections"][label]
                y=getattr(r,col)
                if v is not None and pd.notna(y):
                    records.append({"week":wk,"metric":label,"actual":float(y),"forecast":v})
    result={}
    for metric in STAT_MAP:
        a=[z for z in records if z["metric"]==metric]
        result[metric]={"observations":len(a),
          "MAE":round(sum(abs(x["forecast"]-x["actual"]) for x in a)/len(a),4) if a else None}
    return {"status":"OBSERVED_BOX_ONLY_HISTORICAL_DIAGNOSTIC",
      "metrics":result,"scored_rows":len(records),
      "future_outcome_leakage_blocked_by_week_cutoff":True,
      "absent_box_rows_not_imputed":True,
      "real_book_line_calibration":False,
      "td_probability_calibration":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--week",type=int,default=0)
    p.add_argument("--output-dir",default="output/phase43")
    p.add_argument("--lock-dir",default="snapshots/phase43")
    a=p.parse_args()
    now=datetime.now(timezone.utc)
    folder=Path("private_data");folder.mkdir(exist_ok=True)
    schedule,sh=fetch_schedule(folder)
    frames=[];hashes={"schedule":sh}
    for year in (2025,2026):
        f,meta=download(year,folder);frames.append(f);hashes[str(year)]=meta["sha256"]
    roster,meta=acquire(2026,folder);hashes["roster"]=meta["source_sha256"]
    raw=pd.concat(frames,ignore_index=True)
    out=Path(a.output_dir);out.mkdir(parents=True,exist_ok=True)
    diagnostic=walk_forward(raw)
    future=schedule[(schedule.season==2026)&(schedule.game_type=="REG")&
     (schedule.gameday.astype(str)>now.date().isoformat())&
     (schedule.home_score.isna())&(schedule.away_score.isna())]
    week=a.week or (int(future.sort_values("gameday").iloc[0].week) if len(future) else 0)
    from scripts.phase43_player_eligibility_gate import evaluate as eligibility_audit
    result={"version":VERSION,"target_week":week,
     "diagnostic":diagnostic,"snapshot_status":"NOT_CREATED","snapshot_path":None,
     "sportsbook_requests":0,"qualified_bets":0,
     "eligibility_status":"NO_SNAPSHOT","verified_active_count":0,
     "unverified_count":0}
    if week:
        lockdir=Path(a.lock_dir);lockdir.mkdir(parents=True,exist_ok=True)
        path=lockdir/f"2026-week-{week:02d}.json"
        if path.exists():
            existing=json.loads(path.read_text());verify(existing)
            result["snapshot_status"]="ALREADY_LOCKED_UNCHANGED"
            result["snapshot_path"]=str(path)
            evidence=eligibility_audit(existing)
            result["eligibility_status"]=evidence["status"]
            result["verified_active_count"]=evidence["verified_active_count"]
            result["unverified_count"]=evidence["unverified_count"]
        else:
            try:snap=build(schedule,raw,roster,week,now,hashes)
            except ValueError:
                result["snapshot_status"]="WAITING_FOR_COMPLETED_PRIOR_WEEK_OR_FUTURE_GAME"
            else:
                verify(snap)
                with path.open("x") as f:f.write(json.dumps(snap,indent=2)+"\n")
                result["snapshot_status"]="FROZEN_FUTURE_PROJECTIONS"
                result["snapshot_path"]=str(path)
                result["new_forecasts"]=len(snap["forecasts"])
                evidence=eligibility_audit(snap)
                result["eligibility_status"]=evidence["status"]
                result["verified_active_count"]=evidence["verified_active_count"]
                result["unverified_count"]=evidence["unverified_count"]
    (out/"public_summary.json").write_text(json.dumps(result,indent=2))
    msg=("# GRIDIRON Phase43 — pass, rush & TD forecasting\n\n"
      f"**Next fixture week:** {week or 'none'}. **Freeze:** {result['snapshot_status']}.\n\n"
      f"**Historical observed market metric rows:** {diagnostic['scored_rows']}.\n\n"
      "**Passing and rushing estimates: preliminary baselines. "
      "TD 2+/3+ tails: uncalibrated Poisson heuristics. No bet picks or API requests.**\n")
    print(msg)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write(msg)
if __name__=="__main__":main()
