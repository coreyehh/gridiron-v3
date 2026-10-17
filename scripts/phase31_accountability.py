"""Phase 31: immutable pregame forecast snapshots and scored accountability.

Forecasts are created once per season/week before each selected fixture's DATE,
using only completely scored preceding weeks. Snapshot files are never changed
by this script. Grading reads the actual snapshot, never re-forecasts outcomes.
"""
import argparse,hashlib,json,os
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
from scripts.ingest import download
from scripts.phase18 import fetch_schedule,completed_weeks
from scripts.phase20_opportunity import normalize,team_games,opportunity_forecast
from scripts.phase23_role_model import role_forecast
from scripts.phase15 import acquire

VERSION="phase31-immutable-weekly-accountability-v1"
MODEL="phase23-player-role-with-phase20-volume"
METRICS=("targets","receptions","receiving_yards")

def canonical(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False)
def digest(x):
    return hashlib.sha256(canonical(x).encode()).hexdigest()
def validate_identity(roster):
    names={}
    for r in roster:
        key=(str(r["team"]),str(r["player_id"]))
        if key in names and names[key]!=str(r["player_name"]):
            raise ValueError("Ambiguous current roster")
        names[key]=str(r["player_name"])
    return names

def build_snapshot(schedule,history,roster,asof,week,hashes):
    """Week may be partially played: only future-dated, unscored fixtures appear."""
    if not 4<=week<=18:raise ValueError("Target week must be 4..18")
    now=asof.astimezone(timezone.utc)
    all_games=schedule[(schedule.season==2026)&(schedule.game_type=="REG")&
                        (schedule.week==week)]
    if all_games.empty:raise ValueError("No matching regular-season week")
    future=all_games[(all_games.gameday.astype(str)>now.date().isoformat())&
                     (all_games.home_score.isna())&(all_games.away_score.isna())]
    if future.empty:raise ValueError("No unplayed games strictly after current UTC date")
    allowed=completed_weeks(schedule,week,now.isoformat(),2026)
    if max(allowed,default=0)!=week-1:
        raise ValueError("Previous week not fully completed")
    observed=normalize(history)
    prior=observed[(observed.season==2025)|((observed.season==2026)&
                                             observed.week.isin(allowed))]
    # Fail closed if historical inputs accidentally contain current target-week values.
    if (prior[(prior.season==2026)&(prior.week>=week)]).shape[0]:
        raise ValueError("Target-week leakage")
    teams=team_games(prior)
    names=validate_identity(roster)
    fixtures=[]
    rows=[]
    for game in future.sort_values(["gameday","home_team","away_team"]).itertuples():
        home,away=str(game.home_team),str(game.away_team)
        try:
            volumes=opportunity_forecast(teams,schedule,home,away,allowed)
        except ValueError:
            # Incomplete team histories are not eligibility to guess a prediction.
            continue
        fixture_key=f"2026-W{week:02d}-{away}-at-{home}"
        fixture_rows=[]
        for club in (home,away):
            roles=role_forecast(prior,volumes[club]["pass_attempts"]["projection"],allowed,club)
            for r in roles:
                pid=str(r["player_id"])
                name=names.get((club,pid))
                if not name:continue
                record={"fixture_id":fixture_key,"season":2026,"week":week,
                   "gameday":str(game.gameday),"team":club,"player_id":pid,
                   "player_name":name,"model":MODEL,
                   "targets":round(float(r["targets"]),4),
                   "receptions":round(float(r["receptions"]),4),
                   "receiving_yards":round(float(r["receiving_yards"]),4),
                   "confirmed_active":False,"routes_verified":False}
                fixture_rows.append(record)
        if fixture_rows:
            fixtures.append({"id":fixture_key,"home":home,"away":away,
                  "gameday":str(game.gameday),"player_forecasts":len(fixture_rows),
                  "kickoff_time_verified":False})
            rows.extend(fixture_rows)
    if not rows:raise ValueError("No usable pregame player-role predictions")
    if len({(r["fixture_id"],r["team"],r["player_id"]) for r in rows})!=len(rows):
        raise ValueError("Duplicate fixture/player forecast")
    snapshot={"version":VERSION,"season":2026,"week":week,
      "created_at_utc":now.isoformat(),"snapshot_mode":"strictly_future_dated_games_only",
      "model":MODEL,"source_sha256":hashes,
      "prior_completed_weeks":sorted(allowed),
      "fixtures":fixtures,"forecasts":rows,"qualified_bets":0,
      "official_actives_verified":False,
      "sportsbook_prices_included":False,
      "no_pregame_coverage_or_routes_verified":True}
    snapshot["payload_sha256"]=digest(snapshot)
    return snapshot

def verify_snapshot(snapshot,asof=None):
    copy=dict(snapshot);hashval=copy.pop("payload_sha256",None)
    if not hashval or digest(copy)!=hashval:raise ValueError("Forecast snapshot hash mismatch")
    if snapshot.get("model")!=MODEL or snapshot.get("season")!=2026:raise ValueError("Unknown model/year")
    if not 4<=int(snapshot.get("week",0))<=18:raise ValueError("Invalid week")
    at=datetime.fromisoformat(snapshot["created_at_utc"].replace("Z","+00:00"))
    if at.tzinfo is None:raise ValueError("Timestamp lacks timezone")
    if asof and at>asof:raise ValueError("Future timestamp")
    seen=set()
    future_games={f["id"]:f for f in snapshot["fixtures"]}
    for f in future_games.values():
        if f["gameday"]<=at.date().isoformat():
            raise ValueError("Game not strictly future-dated at lock")
    for r in snapshot["forecasts"]:
        key=(r["fixture_id"],r["team"],r["player_id"])
        if key in seen:raise ValueError("Duplicate prediction")
        seen.add(key)
        if r["fixture_id"] not in future_games:raise ValueError("Unmatched fixture")
        if r["week"]!=snapshot["week"] or r["model"]!=MODEL:raise ValueError("Mixed forecast models")
        if r["team"] not in (future_games[r["fixture_id"]]["home"],future_games[r["fixture_id"]]["away"]):
            raise ValueError("Player team not playing")
    return True

def grade_snapshot(snapshot,schedule,history,asof):
    verify_snapshot(snapshot,asof)
    week=int(snapshot["week"])
    target=schedule[(schedule.season==2026)&(schedule.week==week)&(schedule.game_type=="REG")]
    if target.empty or target[["home_score","away_score"]].isna().any().any():
        return {"week":week,"status":"waiting_for_completed_week","graded":0,
          "unknown_participation":0,"predictions":len(snapshot["forecasts"])}
    if any(str(x)>asof.date().isoformat() for x in target.gameday):
        return {"week":week,"status":"waiting_for_game_dates","graded":0,
          "unknown_participation":0,"predictions":len(snapshot["forecasts"])}
    stats=normalize(history)
    current=stats[(stats.season==2026)&(stats.week==week)]
    # Missing data is UNKNOWN. Zero production must be explicit in the box source.
    grouped=current.set_index(["team_code","player_id"])
    result=[]
    unresolved=[]
    for r in snapshot["forecasts"]:
        key=(r["team"],r["player_id"])
        if key not in grouped.index:
            unresolved.append({"fixture_id":r["fixture_id"],"player_id":r["player_id"],
                               "team":r["team"],"reason":"not_in_player_week_stat_source"})
            continue
        actual=grouped.loc[key]
        errors={m:round(float(actual[m])-float(r[m]),4) for m in METRICS}
        result.append({"fixture_id":r["fixture_id"],"player_id":r["player_id"],
          "team":r["team"],"errors":errors})
    summaries={}
    for m in METRICS:
        ae=[abs(x["errors"][m]) for x in result]
        summaries[m]={"n":len(ae),"mae":round(sum(ae)/len(ae),4) if ae else None}
    return {"week":week,
      "status":"graded_participation_unknown_excluded" if unresolved else "graded",
      "graded":len(result),"unknown_participation":len(unresolved),
      "predictions":len(snapshot["forecasts"]),
      "metric_summary":summaries,"per_player_errors":result,
      "unknown_player_rows":unresolved,
      "excluded_absence_not_confirmed_inactive":True}

def choose_week(schedule,asof):
    future=schedule[(schedule.season==2026)&(schedule.game_type=="REG")&
      (schedule.gameday.astype(str)>asof.date().isoformat())&
      (schedule.home_score.isna())&(schedule.away_score.isna())]
    if future.empty:return None
    return int(future.sort_values(["gameday","week"]).iloc[0].week)

def audit(snapshot_folder,schedule,history,roster,asof,hashes,requested_week=None):
    folder=Path(snapshot_folder)
    folder.mkdir(parents=True,exist_ok=True)
    week=requested_week or choose_week(schedule,asof)
    created=None; skipped=None
    if week is None:
        skipped="no_future_dated_unscored_regular_season_game"
    else:
        path=folder/f"2026-week-{week:02d}.json"
        if path.exists():
            verify_snapshot(json.loads(path.read_text()),asof)
            skipped="immutable_week_snapshot_already_exists"
        else:
            try:
                snap=build_snapshot(schedule,history,roster,asof,week,hashes)
            except ValueError as exc:
                skipped=str(exc)
            else:
                # Exclusive create; preserve past decisions, never silently overwrite.
                with path.open("x",encoding="utf-8") as f:
                    f.write(json.dumps(snap,indent=2)+"\n")
                created=str(path)
    history_grades=[]
    for path in sorted(folder.glob("2026-week-*.json")):
        frozen=json.loads(path.read_text())
        history_grades.append(grade_snapshot(frozen,schedule,history,asof))
    complete=[g for g in history_grades if g["status"].startswith("graded")]
    n=sum(g["graded"] for g in complete)
    cumulative={}
    for m in METRICS:
        total=sum(g["metric_summary"][m]["mae"]*g["graded"]
                  for g in complete if g["metric_summary"][m]["mae"] is not None)
        cumulative[m]={"n":n,"mae":round(total/n,4) if n else None}
    return {"version":VERSION,"evaluated_at_utc":asof.isoformat(),
      "snapshot_created":created,"snapshot_skipped_reason":skipped,
      "snapshot_files":len(history_grades),
      "completed_week_snapshots":len(complete),
      "graded_player_games":n,
      "unknown_player_game_rows":sum(g.get("unknown_participation",0) for g in history_grades),
      "metric_summary":cumulative,
      "weekly":history_grades,
      "prospective_coverage_is_partial":True,
      "source_publication_asof_attestation":False,
      "missing_box_row_treated_as_zero":False,
      "bets_qualified":0,"sportsbook_profitability_evaluated":False}

def markdown(out):
    lines=["# GRIDIRON Phase 31 — Weekly immutable forecast accountability","",
      f"**Frozen new snapshot:** {out['snapshot_created'] or 'none'}",
      f"**Capture note:** {out['snapshot_skipped_reason'] or 'new future-dated snapshot locked'}",
      f"**Frozen weeks:** {out['snapshot_files']}; **scored snapshot weeks:** {out['completed_week_snapshots']}",
      f"**Scored player-games with observed box rows:** {out['graded_player_games']}; **unresolved box rows:** {out['unknown_player_game_rows']}","",
      "## Cumulative observed-player accuracy (not a betting hit rate)","",
      "| Metric | Graded player-games | MAE |","|:--|--:|--:|"]
    for m,d in out["metric_summary"].items():
        lines.append(f"| {m} | {d['n']} | {d['mae'] if d['mae'] is not None else 'not available'} |")
    lines+=["","## Per-snapshot status","",
      "| Week | Status | Graded | Unknown box rows |","|--:|:--|--:|--:|"]
    for g in out["weekly"]:
        lines.append(f"| {g['week']} | {g['status']} | {g['graded']} | {g['unknown_participation']} |")
    lines+=["","**Important:** forecast locks are immutable, but current source publication-time evidence is not independently attested. Games with scores do not prove missing player rows were inactives, so those rows are ungraded.",
       "**This is a prospective research accuracy ledger, NOT actual sportsbook picks or ROI.**",""]
    return "\n".join(lines)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--week",type=int,default=0)
    parser.add_argument("--snapshot-dir",default="snapshots/phase31")
    parser.add_argument("--output",default="output/phase31_accountability.json")
    args=parser.parse_args()
    if args.week and not 4<=args.week<=18:parser.error("--week 0 or 4..18")
    asof=datetime.now(timezone.utc)
    private=Path("private_data");private.mkdir(exist_ok=True)
    schedule,sh=fetch_schedule(private);frames=[];hashes={"schedule":sh}
    for yr in (2025,2026):
        data,meta=download(yr,private);frames.append(data);hashes[str(yr)]=meta["sha256"]
    roster,ra=acquire(2026,private);hashes["roster"]=ra["source_sha256"]
    result=audit(args.snapshot_dir,schedule,pd.concat(frames,ignore_index=True),
                roster,asof,hashes,args.week or None)
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2))
    page=markdown(result);print(page)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write(page)
if __name__=="__main__":main()
