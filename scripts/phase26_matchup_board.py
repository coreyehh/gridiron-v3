"""GRIDIRON Phase 26: integrated matchup research board, fail-closed on betting.

Authentic nflverse team/player history + 2026 roster identities; Phase20 team
opportunity, Phase23 receiving-role challenger, Phase24 empirical residual
frequencies for ILLUSTRATIVE thresholds, optional Phase25 one-game bookmaker
coverage audit. No false claim of real-book probability calibration.
"""
import argparse,json,os
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
from scripts.ingest import download
from scripts.phase18 import fetch_schedule,completed_weeks
from scripts.phase15 import acquire,team_code
from scripts.phase20_opportunity import normalize,team_games,opportunity_forecast,player_forecast
from scripts.phase23_role_model import role_forecast
from scripts.phase24_participation_calibration import LEVELS,MIN_HISTORY,empirical_probability,candidate_predictions
from scripts.phase25_market_gate import live_once

VERSION="phase26-integrated-matchup-research-v1"
EXAMPLE_LINES={"receptions":3.5,"receiving_yards":54.5}

def pick_game(schedule,team_a="",team_b="",week=0,asof=None):
    now=asof or datetime.now(timezone.utc)
    games=schedule[(schedule.season==2026)&(schedule.game_type=="REG")].copy()
    if week:games=games[games.week==week]
    if bool(team_a)!=bool(team_b):raise ValueError("Specify both teams or neither")
    if team_a:
        a,b=team_code(team_a),team_code(team_b)
        if a==b:raise ValueError("Two distinct teams required")
        games=games[((games.home_team==a)&(games.away_team==b))|
                    ((games.home_team==b)&(games.away_team==a))]
        if len(games)!=1:raise ValueError("Exact matchup not uniquely scheduled")
        g=games.iloc[0]
        if str(g.gameday)<now.date().isoformat():
            raise ValueError("Matchup date is in the past")
    else:
        # Use a date strictly after today: same-day kickoffs aren't proven
        # future without independently verified kickoff time.
        games=games[games.gameday.astype(str)>now.date().isoformat()]
        if games.empty:raise ValueError("No strictly future matchup found")
        g=games.sort_values(["gameday","week","home_team","away_team"]).iloc[0]
    if pd.notna(g.home_score) or pd.notna(g.away_score):
        raise ValueError("Matchup has recorded results; not eligible as pregame research")
    return {"week":int(g.week),"home":str(g.home_team),"away":str(g.away_team),
      "gameday":str(g.gameday),"kickoff_time_not_verified":True}

def historical_residuals(history,games,schedule,target_week,allowed):
    """Completed historical weeks only; no outcome from target week or later."""
    residuals=defaultdict(list);trained=[]
    for week in range(4,target_week):
        if week not in allowed or week-1 not in allowed:continue
        earlier={w for w in allowed if w<week}
        prev=history[(history.season==2025)|((history.season==2026)&history.week.isin(earlier))]
        truth=history[(history.season==2026)&(history.week==week)]
        fixtures=schedule[(schedule.season==2026)&(schedule.week==week)&(schedule.game_type=="REG")]
        pending=[]
        for g in fixtures.itertuples():
            try:preds=candidate_predictions(prev,games,schedule,week,str(g.home_team),str(g.away_team),earlier)
            except ValueError:continue
            for (club,pid),forecast in preds.items():
                row=truth[(truth.team_code==club)&(truth.player_id==pid)]
                for market in EXAMPLE_LINES:
                    actual=float(row.iloc[0][market]) if len(row)==1 else 0.
                    pending.append((market,actual-float(forecast[market])))
        for metric,diff in pending:residuals[metric].append(diff)
        trained.append(week)
    return residuals,trained

def build(schedule,history,roster,team_a="",team_b="",week=0,asof=None,source_hashes=None):
    now=asof or datetime.now(timezone.utc)
    event=pick_game(schedule,team_a,team_b,week,now)
    allowed=completed_weeks(schedule,event["week"],now.isoformat(),2026)
    if not allowed or max(allowed)!=event["week"]-1:
        raise ValueError("All preceding regular-season weeks must be scored")
    clean=normalize(history)
    past=clean[(clean.season==2025)|((clean.season==2026)&clean.week.isin(allowed))]
    games=team_games(past)
    home,away=event["home"],event["away"]
    projection=opportunity_forecast(games,schedule,home,away,allowed)
    historical,trained=historical_residuals(past,games,schedule,event["week"],allowed)
    identity={(x["player_id"],x["team"]):x["player_name"] for x in roster}
    players=[]
    for club in (home,away):
        baseline=player_forecast(past,projection[club],allowed,club)
        updated=role_forecast(past,projection[club]["pass_attempts"]["projection"],allowed,club)
        updated_map={x["player_id"]:x for x in updated}
        for row in baseline:
            pid=row["player_id"]; role=updated_map.get(pid)
            if not role:continue
            probs={}
            for market,threshold in EXAMPLE_LINES.items():
                probs[market]=empirical_probability(
                    historical[market],float(role[market]),threshold)
            players.append({
              "player_id":pid,"player":identity.get((pid,club)) or "Unmatched identity",
              "team":club,"position":row["position"],
              "targets":round(float(role["targets"]),2),
              "receptions":round(float(role["receptions"]),2),
              "receiving_yards":round(float(role["receiving_yards"]),2),
              "recent_share":round(float(role["targets_last2_share"]),4),
              "prior_five_share":round(float(role["targets_last5_share"]),4),
              "illustrative_threshold_probabilities":{
                market:{"threshold":EXAMPLE_LINES[market],
                  "over_probability":round(float(p),4) if p is not None else None,
                  "training_residual_n":len(historical[market])}
                for market,p in probs.items()},
              "roster_identity_matched":(pid,club) in identity,
              "game_day_active_confirmed":False,
              "route_participation_confirmed":False,
              "price_specific_probability_validated":False,
              "bet_status":"RESEARCH_ONLY"})
    players.sort(key=lambda x:x["targets"],reverse=True)
    result={"version":VERSION,"status":"integrated_public_research_no_qualified_bets",
       "game":event,"completed_weeks":sorted(allowed),
       "team_projection":projection,"player_forecasts":players,
       "historical_probability_training_weeks":trained,
       "source_hashes":source_hashes or {},
       "team_volume_model":"phase20",
       "player_allocation_model":"phase23_candidate",
       "historical_residual_probability_model":"phase24 illustrative thresholds",
       "phase22_challenger_not_integrated":True,
       "game_day_actives_verified":False,
       "player_routes_verified":False,"defensive_coverage_verified":False,
       "game_day_kickoff_time_verified":False,
       "actual_bookmaker_lines_in_public_report":False,
       "calibrated_real_line_probabilities":False,
       "qualified_bets":0}
    return result

def markdown(report):
    e=report["game"]
    lines=["# GRIDIRON Phase 26 — End-to-end matchup research","",
      f"**{e['away']} @ {e['home']} — Week {e['week']}, {e['gameday']}**",
      "**RESEARCH ONLY · 0 qualified bets · no verified game-day actives**","",
      "## Team volume","",
      "| Team | Projected pass attempts | Projected rush attempts |",
      "|:--|--:|--:|"]
    for team,r in report["team_projection"].items():
        lines.append(f"| {team} | {r['pass_attempts']['projection']:.1f} | {r['rush_attempts']['projection']:.1f} |")
    lines+=["","## Player receiving opportunity","",
      "| Player | Team | Targets | Receptions | Receiving yards |",
      "|:--|:--|--:|--:|--:|"]
    for p in report["player_forecasts"][:24]:
        lines.append(f"| {p['player']} | {p['team']} | {p['targets']:.1f} | {p['receptions']:.1f} | {p['receiving_yards']:.1f} |")
    lines+=["","## Illustrative probabilities (NOT real offered lines)","",
      "| Player | P(over 3.5 receptions) | P(over 54.5 rec yards) |",
      "|:--|--:|--:|"]
    for p in report["player_forecasts"][:16]:
        values=[p["illustrative_threshold_probabilities"][m]["over_probability"]
                for m in ("receptions","receiving_yards")]
        fmt=lambda x:f"{x:.0%}" if x is not None else "insufficient history"
        lines.append(f"| {p['player']} | {fmt(values[0])} | {fmt(values[1])} |")
    lines+=["","**Market and eligibility:** bookmaker ingestion may be checked separately for this game, but this public board never exports licensed player odds. No independently verified actives, routes, injury changes, matchup coverage or pre-quote book-line calibration.",
      f"Historical probability residual training weeks: {report['historical_probability_training_weeks'] or 'none'}. Absence from stats is not proof of inactive status.",
      "**Do not use illustrative probabilities to infer a price edge.**",""]
    return "\n".join(lines)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--team-a",default="")
    p.add_argument("--team-b",default="")
    p.add_argument("--week",type=int,default=0)
    p.add_argument("--live-market-audit",action="store_true",
                   help="Explicitly opt into one game of paid bookmaker quotes")
    p.add_argument("--region",choices=("us","us2","ca"),default="us")
    p.add_argument("--output",default="output/phase26_research.json")
    a=p.parse_args()
    folder=Path("private_data");folder.mkdir(exist_ok=True)
    schedule,hash_s=fetch_schedule(folder)
    frames=[];hashes={"schedule":hash_s}
    for year in (2025,2026):
        f,meta=download(year,folder);frames.append(f);hashes[str(year)]=meta["sha256"]
    roster,audit=acquire(2026,folder);hashes["roster"]=audit["source_sha256"]
    report=build(schedule,pd.concat(frames,ignore_index=True),roster,
       a.team_a,a.team_b,a.week,source_hashes=hashes)
    if a.live_market_audit:
        game=report["game"]
        market=live_once(os.environ.get("ODDS_API_KEY"),a.region,game["home"],game["away"])
        report["real_market_integrity_aggregate"]=market
        report["qualified_bets"]=0
    output=Path(a.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2))
    doc=markdown(report)
    if a.live_market_audit:
        m=report["real_market_integrity_aggregate"]
        doc+="\n## Matched live market coverage (counts only)\n\n"
        doc+=f"Status: {m['status']}; valid two-sided pairs: {m.get('counts',{}).get('valid_two_sided_pairs',0)}. Zero eligible wagers.\n"
    print(doc)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write(doc)
if __name__=="__main__":main()
