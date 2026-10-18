"""Phase43 supplemental Week6 pre-kickoff forecasts for remaining Sunday games.

Never backfills a match after its verified scheduled kickoff. Uses nflverse
gameday + gametime interpreted in America/New_York, with DST, and never
overwrites the earlier immutable Phase43 weekly snapshot.
"""
import argparse,json,os,re
from datetime import datetime,timezone,time
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
from scripts.phase43_multimarket_forecasts import VERSION,prep,forecast_player,verify
from scripts.phase31_accountability import digest,validate_identity
from scripts.phase18 import fetch_schedule,completed_weeks
from scripts.ingest import download
from scripts.phase15 import acquire

LOCAL=ZoneInfo("America/New_York")
VERSION_SUPPLEMENT="phase43-week6-remaining-future-kickoff-only-v1"

def verified_kickoff(game):
    """Strict game day + time, known zone; reject absent/ambiguous kickoff."""
    day=str(game["gameday"])
    clock=game.get("gametime")
    if not re.fullmatch(r"20\d\d-\d\d-\d\d",day):
        raise ValueError("Invalid NFL game date")
    if not isinstance(clock,str) or not re.fullmatch(r"(?:[01]?\d|2[0-3]):[0-5]\d",clock):
        raise ValueError("Missing/invalid official schedule gametime")
    hour,minute=map(int,clock.split(":"))
    local=datetime.fromisoformat(day).replace(hour=hour,minute=minute,tzinfo=LOCAL)
    # Reject DST nonexistent timestamps and unresolvable source time.
    if local.astimezone(timezone.utc).astimezone(LOCAL).replace(fold=local.fold)!=local:
        raise ValueError("Invalid DST-local scheduled kickoff")
    return local.astimezone(timezone.utc)

def future_fixtures(schedule,week,now):
    if now.tzinfo is None:raise ValueError("Timezone-aware UTC now required")
    now=now.astimezone(timezone.utc)
    subset=schedule[(schedule.season==2026)&(schedule.week==week)&
                    (schedule.game_type=="REG")].copy()
    accepted=[];excluded=[]
    if "gametime" not in subset.columns:
        raise ValueError("No NFL kickoff clock column: cannot safely capture same-day fixture")
    for _,g in subset.iterrows():
        ident=f"2026-W{week:02d}-{g.away_team}-at-{g.home_team}"
        try:kick=verified_kickoff(g)
        except (ValueError,TypeError):
            excluded.append({"fixture_id":ident,"reason":"MISSING_VERIFIABLE_KICKOFF"})
            continue
        if pd.notna(g.home_score) or pd.notna(g.away_score):
            excluded.append({"fixture_id":ident,"reason":"ALREADY_SCORED_OR_SCORE_PARTIAL"})
        elif kick<=now:
            excluded.append({"fixture_id":ident,"reason":"KICKOFF_ALREADY_PASSED"})
        else:
            accepted.append({"id":ident,"home":str(g.home_team),"away":str(g.away_team),
                "gameday":str(g.gameday),"kickoff_utc":kick.isoformat()})
    return accepted,excluded

def build_remaining(schedule,history,roster,asof,hashes,week=6):
    """Only strictly future fixtures, only 2025+completed Week 1..week-1."""
    if asof.tzinfo is None:raise ValueError("Aware asof required")
    now=asof.astimezone(timezone.utc)
    if week!=6:raise ValueError("This repair targets only the Week6 remaining slate")
    allowed=completed_weeks(schedule,week,now.isoformat(),2026)
    if max(allowed,default=0)!=week-1:
        raise ValueError("Incomplete previous week — do not leak earlier results")
    fixtures,excluded=future_fixtures(schedule,week,now)
    if not fixtures:return None,{"status":"NO_UNSTARTED_WEEK6_FIXTURES",
       "excluded":excluded,"fixtures":0,"forecast_count":0}
    frame=prep(history)
    prior=frame[(frame.season==2025)|((frame.season==2026)&(frame.week.isin(allowed)))]
    if len(prior[(prior.season==2026)&(prior.week>=week)]):
        raise ValueError("Future week player data in training")
    names=validate_identity(roster)
    roles={(str(r["team"]),str(r["player_id"])):str(r.get("position",""))
            for r in roster}
    forecasts=[]
    for f in fixtures:
        for team in (f["home"],f["away"]):
            for (club,pid),name in sorted(names.items()):
                if club!=team:continue
                obs=prior[(prior.team_code==team)&(prior.player_id.astype(str)==pid)]
                if obs.empty:continue
                pos=roles[(club,pid)] or str(obs.iloc[-1].position)
                if pos not in ("QB","RB","WR","TE"):continue
                pred=forecast_player(obs,pos)
                if pred is None:continue
                forecasts.append({"fixture_id":f["id"],"team":team,
                  "player_id":pid,"player_name":name,**pred})
    snapshot={"version":VERSION_SUPPLEMENT,"phase43_model_version":VERSION,
      "season":2026,"week":week,"created_at_utc":now.isoformat(),
      "model":"historical_obs_shrunk_mean_and_uncalibrated_td_poisson",
      "source_sha256":hashes,"prior_completed_weeks":sorted(allowed),
      "fixtures":fixtures,"forecasts":forecasts,
      "excluded_fixtures":excluded,"uses_sportsbook_odds":False,
      "qualified_bets":0,"official_actives_verified":False,
      "point_in_time_and_kickoff_checked":True,
      "touchdown_probabilities_calibrated":False}
    snapshot["payload_sha256"]=digest(snapshot)
    check_remaining(snapshot)
    return snapshot,{"status":"FROZEN_UNSTARTED_FIXTURES","fixtures":len(fixtures),
     "forecast_count":len(forecasts),"excluded":excluded}

def check_remaining(snapshot):
    orig=dict(snapshot);checksum=orig.pop("payload_sha256",None)
    if snapshot.get("version")!=VERSION_SUPPLEMENT or checksum!=digest(orig):
        raise ValueError("Supplement hash mismatch")
    lock=datetime.fromisoformat(snapshot["created_at_utc"])
    if lock.tzinfo is None:raise ValueError("No capture timezone")
    ids={f["id"] for f in snapshot["fixtures"]}
    if len(ids)!=len(snapshot["fixtures"]):raise ValueError("Duplicate fixtures")
    for f in snapshot["fixtures"]:
        if datetime.fromisoformat(f["kickoff_utc"])<=lock:
            raise ValueError("Pregame snapshot includes already-kicked-off fixture")
    seen=set()
    for row in snapshot["forecasts"]:
        key=(row["fixture_id"],row["team"],row["player_id"])
        if row["fixture_id"] not in ids or key in seen:raise ValueError("Invalid forecast identity")
        seen.add(key)
    return True

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",default="output/phase43-remaining")
    p.add_argument("--lock-dir",default="snapshots/phase43/remaining")
    a=p.parse_args()
    now=datetime.now(timezone.utc)
    folder=Path("private_data");folder.mkdir(exist_ok=True)
    schedule,sh=fetch_schedule(folder)
    frames=[];hashes={"schedule":sh}
    for year in (2025,2026):
        df,metadata=download(year,folder)
        frames.append(df);hashes[str(year)]=metadata["sha256"]
    roster,roster_info=acquire(2026,folder);hashes["roster"]=roster_info["source_sha256"]
    snap,report=build_remaining(schedule,pd.concat(frames,ignore_index=True),
                                roster,now,hashes)
    output=Path(a.output_dir);output.mkdir(parents=True,exist_ok=True)
    result={"version":VERSION_SUPPLEMENT,"week":6,"captured_at_utc":now.isoformat(),
      **report,"new_api_requests":0,"qualified_bets":0}
    if snap is not None:
        path=Path(a.lock_dir);path.mkdir(parents=True,exist_ok=True)
        dest=path/("2026-week-06-remaining-"+now.strftime("%Y%m%dT%H%M%SZ")+".json")
        with dest.open("x") as f:f.write(json.dumps(snap,indent=2)+"\n")
        result["snapshot_path"]=str(dest)
        # Nonbookmaker projections are public: directly readable HTML/CSV.
        table=[]
        for row in snap["forecasts"]:
            p=row["point_projections"]
            table.append({"fixture":row["fixture_id"],"player":row["player_name"],
                "team":row["team"],"position":row["position"],
                "passing_yards":p["passing_yards"],
                "passing_attempts":p["pass_attempts"],
                "completions":p["completions"],
                "rushing_yards":p["rushing_yards"],
                "rush_attempts":p["rush_attempts"],
                "anytime_td_unvalidated":p["anytime_touchdown"],
                "two_plus_td_unvalidated":p["two_plus_touchdowns"],
                "three_plus_td_unvalidated":p["three_plus_touchdowns"],
                "decision":"RESEARCH_ONLY"})
        pd.DataFrame(table).to_csv(output/"week6_remaining_projections.csv",index=False)
        result["games"]=[{"id":g["id"],"kickoff_utc":g["kickoff_utc"]} for g in snap["fixtures"]]
    (output/"public_summary.json").write_text(json.dumps(result,indent=2))
    msg=(f"# Week 6 remaining kickoffs, Phase43 repair\n\n"
         f"**Status:** {report['status']}\n\n"
         f"**Unstarted fixtures:** {report['fixtures']}; "
         f"**new player forecast rows:** {report['forecast_count']}.\n\n"
         "Previously started games excluded. Original Week6 snapshot untouched. "
         "TD probability heuristics uncalibrated; zero official picks.\n")
    print(msg)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write(msg)
if __name__=="__main__":main()
