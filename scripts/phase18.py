"""Phase 18: 2026 prior-completed-week forecasts, frozen BEFORE paid bookmaker quotes.
Research-only: no verified actives, opponent schematics, calibrated lines, or betting edges.
"""
import argparse,hashlib,json,os,shutil
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
from collections import Counter
import pandas as pd
from scripts.ingest import download,MEASURES
from scripts.phase15 import acquire
from scripts.phase17 import fit_models,FEATURES,MIN_HISTORY
from scripts.phase14 import identity,utc
from scripts.phase16 import team_id
from scripts.live_market import normalize,summarize
from scripts.live_odds_smoke import fetch_json,SPORT,MARKETS,DEFAULT_BOOKS

SCHEDULE_URL="https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
VERSION="phase18-2026-previous-completed-weeks-v1"
def now():return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def jsonhash(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def fetch_schedule(folder):
    path=folder/"schedule.csv"
    req=Request(SCHEDULE_URL,headers={"User-Agent":"GRIDIRON-v3/1.0"})
    with urlopen(req,timeout=90) as response,path.open("wb") as file:shutil.copyfileobj(response,file)
    df=pd.read_csv(path,low_memory=False)
    needed={"season","week","home_team","away_team","home_score","away_score","game_type","gameday"}
    if not needed.issubset(df.columns):raise ValueError("Missing schedule columns")
    return df,sha(path)
def target_game(schedule,season,home,away,kickoff,asof):
    # Exact game-day + teams + season and uniquely scheduled game.
    date=utc(kickoff).date().isoformat()
    matching=schedule[(schedule.season==season)&(schedule.home_team==home)&
                      (schedule.away_team==away)&(schedule.gameday.astype(str)==date)]
    if len(matching)!=1:raise ValueError("Event cannot be uniquely mapped to season schedule")
    game=matching.iloc[0]
    if game.game_type!="REG":raise ValueError("Only regular season evaluated")
    if not 1<=int(game.week)<=18:raise ValueError("Invalid target week")
    if utc(kickoff)<=utc(asof):raise ValueError("Game already started")
    return int(game.week)
def completed_weeks(schedule,target_week,asof,season=2026):
    if target_week<=1:return set()
    subset=schedule[(schedule.season==season)&(schedule.game_type=="REG")&
                    (schedule.week<target_week)].copy()
    allowed=set()
    for wk in range(1,target_week):
        games=subset[subset.week==wk]
        if games.empty:break
        if games[["home_score","away_score"]].isna().any().any():break
        # No future-dated final scores may be used.
        if any(str(day)>utc(asof).date().isoformat() for day in games.gameday):break
        allowed.add(wk)
    return allowed
def frozen_features(frame):
    if frame.empty:raise ValueError("No history")
    if frame.duplicated(["season","week","player_id"]).any():raise ValueError("Duplicate player weeks")
    features={}
    x=frame.sort_values(["player_id","season","week"])
    for pid,g in x.groupby("player_id",sort=False):
        if len(g)<MIN_HISTORY:continue
        last=g.tail(5)
        rec={"position":str(g.iloc[-1].position).upper(),
             "last_season":int(g.iloc[-1].season),"last_week":int(g.iloc[-1].week),
             "observed_2026":int((g.season==2026).sum())}
        for m in MEASURES:
            rec["prior5_"+m]=float(pd.to_numeric(last[m],errors="coerce").mean())
            rec["prior3_"+m]=float(pd.to_numeric(last.tail(3)[m],errors="coerce").mean())
        features[str(pid)]=rec
    return features
def forecast_prequote(roster,history,schedule,event,hashes,asof):
    season=2026
    if not event.get("id") or not event.get("commence_time"):raise ValueError("Invalid event")
    home=team_id(event.get("home_team"));away=team_id(event.get("away_team"))
    if not home or not away or home==away:raise ValueError("Unmapped matchup")
    week=target_game(schedule,season,home,away,event["commence_time"],asof)
    weeks=completed_weeks(schedule,week,asof,season)
    # Reject all noncompleted weeks, including currently in progress.
    permitted=history[(history.season<2026)|((history.season==2026)&history.week.isin(weeks))].copy()
    if not len(permitted[permitted.season==2026]) and weeks:
        raise ValueError("Completed 2026 weeks reported but stats feed contains none")
    model_training=permitted[permitted.season<=2025].copy()
    models=fit_models(model_training)
    if not models:raise ValueError("Missing fitted models")
    available=frozen_features(permitted)
    provenance=jsonhash({"hashes":hashes,"weeks":sorted(weeks),"version":VERSION,
                         "event_id":event["id"],"asof_utc":asof})
    predictions=[]; missing=0;with_current=0
    for r in roster:
        if r.get("season")!=season or r.get("team") not in (home,away):continue
        pid=r["player_id"]
        feat=available.get(pid)
        if feat is None:
            missing+=1;continue
        pos=feat["position"]
        if pos not in ("RB","WR","TE"):continue
        if feat["observed_2026"]>0:with_current+=1
        for market in ("receptions","receiving_yards"):
            model=models.get((pos,market))
            if model is None:continue
            import pandas as pd
            val=max(0.,float(model.predict(pd.DataFrame([{k:feat[k] for k in FEATURES}]))[0]))
            predictions.append({"event_id":event["id"],"player_id":pid,
                "market":market,"point_projection":round(val,3),"created_at_utc":asof,
                "model_version":VERSION,"input_snapshot_sha256":provenance,
                "last_observed_season":feat["last_season"],"last_observed_week":feat["last_week"],
                "observed_games_2026":feat["observed_2026"],
                "official_game_day_active_verified":False,
                "model_probability":None,"decision":"INSUFFICIENT_DATA"})
    if len({(p["player_id"],p["market"]) for p in predictions})!=len(predictions):
        raise ValueError("Duplicate identity forecast")
    return predictions,{"target_week":week,"allowed_completed_2026_weeks":sorted(weeks),
        "forecast_count":len(predictions),"roster_missing_prior_history":missing,
        "players_with_2026_observations":with_current,
        "input_snapshot_sha256":provenance,"created_at_utc":asof}
def compare(predictions,quotes,roster,locked):
    # Separate from forecasting: never touch any bookmaker quote until AFTER lock.
    if quotes and (not locked.get("sha256") or not locked.get("locked_at_utc")):
        raise ValueError("Missing immutable lock")
    pmap={(p["event_id"],p["player_id"],p["market"]):p for p in predictions}
    count=Counter(); gaps={"receptions":[],"receiving_yards":[]};players=set()
    for q in quotes:
        if utc(q["captured_at_utc"])<=utc(locked["locked_at_utc"]):
            raise ValueError("Quote capture predates prediction lock")
        # Require bookmaker's own last-update timestamp AFTER lock, too.
        if utc(q["quoted_at_utc"])<utc(locked["locked_at_utc"]):
            count["quote_timestamp_not_after_lock"]+=1;continue
        home=team_id(q.get("home_team"));away=team_id(q.get("away_team"))
        if not home or not away:count["unmapped_team"]+=1;continue
        status,pid=identity({**q,"home_team":home,"away_team":away},roster)
        if status!="IDENTITY_MATCHED_NOT_ACTIVE_VERIFIED":
            count["unresolved_identity"]+=1;continue
        pred=pmap.get((q["event_id"],pid,q["market"]))
        if pred is None:count["no_locked_projection"]+=1;continue
        if utc(pred["created_at_utc"])>utc(q["quoted_at_utc"]):
            raise ValueError("Projection was generated after quote")
        gap=pred["point_projection"]-float(q["line"])
        gaps[q["market"]].append(gap)
        players.add(pid)
        count["compared_outcomes"]+=1
    return {"matched_distinct_players":len(players),
        "quote_outcomes_total":len(quotes),
        "quote_outcomes_comparable":count["compared_outcomes"],
        "quoted_before_lock_excluded":count["quote_timestamp_not_after_lock"],
        "unresolved_identity":count["unresolved_identity"],
        "without_projection":count["no_locked_projection"],
        "per_market":{k:{"count":len(v),"projection_above_line":sum(x>0 for x in v),
            "projection_below_line":sum(x<0 for x in v),
            "mean_absolute_gap":round(sum(abs(x) for x in v)/len(v),3) if v else None}
            for k,v in gaps.items()},
        "calibrated_probability_available":False,"bets_qualified":0}
def execute(key,region,folder):
    if not key:raise ValueError("ODDS_API_KEY missing")
    # Free event discovery chooses target BEFORE paid market quote call.
    events,_=fetch_json("/v4/sports/"+SPORT+"/events",{},key)
    upcoming=sorted((e for e in events if e.get("id") and e.get("commence_time")
                     and utc(e["commence_time"])>utc(now())),key=lambda x:x["commence_time"])
    if not upcoming:return {"status":"no_upcoming_game","bets_qualified":0}
    event=upcoming[0]
    roster,ra=acquire(2026,folder)
    sch,sch_sha=fetch_schedule(folder)
    frames=[]; hashes={"roster":ra["source_sha256"],"schedule":sch_sha}
    for yr in range(2021,2027):
        frame,meta=download(yr,folder)
        frames.append(frame);hashes[str(yr)]=meta["sha256"]
    history=pd.concat(frames,ignore_index=True)
    asof=now()
    predictions,meta=forecast_prequote(roster,history,sch,event,hashes,asof)
    if not predictions:raise ValueError("No prequote projections, refusing paid odds request")
    # Serialize locked forecasts to private local runner disk, hashed BEFORE paid call.
    path=folder/"phase18_locked_forecasts.json"
    blob={"event_id":event["id"],"lock":meta,"predictions":predictions}
    path.write_text(json.dumps(blob,sort_keys=True,separators=(",",":")))
    os.chmod(path,0o600)
    locked={"sha256":sha(path),"locked_at_utc":now()}
    if utc(locked["locked_at_utc"])>=utc(event["commence_time"]):
        raise ValueError("Game started before lock; no paid odds requested")
    payload,quota=fetch_json("/v4/sports/"+SPORT+"/events/"+event["id"]+"/odds",
          {"regions":region,"markets":",".join(MARKETS),
           "oddsFormat":"american","bookmakers":",".join(DEFAULT_BOOKS)},key)
    captured=now()
    if payload.get("id")!=event["id"]:raise ValueError("Odds changed event")
    quotes=normalize(payload,captured)
    details=compare(predictions,quotes,roster,locked)
    return {"status":"phase18_prospective_form_probe",
        "model_version":VERSION,"locked_forecasts_sha256":locked["sha256"],
        "prediction_locked_at_utc":locked["locked_at_utc"],
        "quote_captured_at_utc":captured,
        "historical_source_hashes":hashes,"roster_source":"nflverse",
        "current_season_stats_included":True,
        "matchup_context_included":False,
        "injury_actives_verified":False,
        "source_publication_time_point_in_time_verified":False,
        "predictions_durable_outside_runner":False,
        "calibrated_betting_probability_available":False,
        "bets_qualified":0,
        "roi_verified":False,
        "quota":quota,**meta,**details}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--live",action="store_true")
    p.add_argument("--region",choices=("us","us2","ca"),default="us")
    p.add_argument("--summary",default="output/phase18_summary.json")
    a=p.parse_args()
    if not a.live:p.error("Run offline tests by default; --live explicitly spends API credits")
    folder=Path("private_data");folder.mkdir(parents=True,exist_ok=True)
    result=execute(os.environ.get("ODDS_API_KEY"),a.region,folder)
    dst=Path(a.summary);dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
