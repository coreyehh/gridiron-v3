"""Phase 27: schedule/rest and opponent-position historical context.

Only verifiable NFLverse player-week and game schedule fields are used.
No inferred injury, routes, coverage, officiating or lineups.
A fixed conservative matchup challenger is compared walk-forward to Phase23.
"""
import argparse,json,os
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
from scripts.ingest import download
from scripts.phase18 import fetch_schedule,completed_weeks
from scripts.phase20_opportunity import normalize,team_games,opportunity_forecast
from scripts.phase23_role_model import role_forecast
from scripts.phase26_matchup_board import build as base_board,pick_game
from scripts.phase15 import acquire

VERSION="phase27-historical-position-matchup-v1"
MIN_SAMPLES=3
WEIGHT=.20

def opponent_history(stats,schedule,defender,allowed,position):
    """Prior opponent WR/RB/TE *targets per offensive pass attempt*.

    Counts are based on the offense's actual player-week stats and schedule,
    not on official coverage assignments, personnel or routes.
    """
    s=schedule[(schedule.season==2026)&(schedule.week.isin(allowed))&
               (schedule.game_type=="REG")&
               ((schedule.home_team==defender)|(schedule.away_team==defender))].copy()
    samples=[]
    for g in s.itertuples():
        offense=g.away_team if g.home_team==defender else g.home_team
        rows=stats[(stats.season==2026)&(stats.week==int(g.week))&
                   (stats.team_code==offense)]
        den=float(rows.loc[rows.position=="QB","attempts"].sum())
        # Team attempts may have non-QB passers; use all instead of QB-only.
        den=float(rows.attempts.sum())
        if den<=0:continue
        num=float(rows.loc[rows.position==position,"targets"].sum())
        samples.append((int(g.week),num/den))
    return sorted(samples)[-5:]

def rest_days(schedule,team,week):
    rows=schedule[(schedule.season==2026)&(schedule.game_type=="REG")&
       ((schedule.home_team==team)|(schedule.away_team==team))&
       (schedule.week<=week)].copy()
    this=rows[rows.week==week]
    prior=rows[rows.week<week].sort_values("week")
    if len(this)!=1 or prior.empty:return None
    x=pd.to_datetime(this.iloc[0].gameday,errors="coerce")
    y=pd.to_datetime(prior.iloc[-1].gameday,errors="coerce")
    if pd.isna(x) or pd.isna(y):return None
    return (x-y).days

def position_multiplier(stats,schedule,defender,allowed,position):
    hist=opponent_history(stats,schedule,defender,allowed,position)
    if len(hist)<MIN_SAMPLES:return 1.,len(hist),None
    # Reference: prior league-wide position targeting, known BEFORE game.
    old=stats[(stats.season==2026)&(stats.week.isin(allowed))]
    denom=float(old.attempts.sum())
    if denom<=0:return 1.,len(hist),None
    league=float(old.loc[old.position==position,"targets"].sum())/denom
    if league<=0:return 1.,len(hist),None
    faced=float(np.mean([x[1] for x in hist]))
    # Low weight, tightly bounded. This estimates target allocation only;
    # positional target rate faced is not a defensive efficiency metric.
    ratio=float(np.clip(faced/league,.75,1.25))
    multiplier=1.+WEIGHT*(ratio-1.)
    return multiplier,len(hist),round(faced,4)

def augment(report,history,schedule,allowed):
    past=normalize(history)
    past=past[(past.season==2025)|((past.season==2026)&past.week.isin(allowed))]
    e=report["game"];home,away=e["home"],e["away"]
    positions={}
    for offense,defender in ((home,away),(away,home)):
        positions[offense]={}
        for pos in ("WR","TE","RB"):
            factor,n,rate=position_multiplier(past,schedule,defender,allowed,pos)
            positions[offense][pos]={"opponent":defender,"multiplier":round(factor,4),
              "defensive_games_sample":n,"prior_position_target_rate_faced":rate}
    # Derived output is challenger only; primary Phase26 model stays unmodified.
    for player in report["player_forecasts"]:
        x=positions.get(player["team"],{}).get(player["position"])
        factor=x["multiplier"] if x else 1.
        player["phase26_targets"]=player["targets"]
        player["phase26_receptions"]=player["receptions"]
        player["phase26_receiving_yards"]=player["receiving_yards"]
        player["phase27_challenger_targets"]=round(player["targets"]*factor,2)
        player["phase27_challenger_receptions"]=round(player["receptions"]*factor,2)
        player["phase27_challenger_receiving_yards"]=round(player["receiving_yards"]*factor,2)
        player["matchup_adjustment_factor"]=factor
        player["verified_game_day_active"]=False
    report["version"]=VERSION
    report["context"]={"home_field_club":home,
      "rest_days_since_prior_game":{c:rest_days(schedule,c,e["week"]) for c in (home,away)},
      "opponent_position_targeting":positions,
      "official_injuries_verified":False,"starting_oline_verified":False,
      "routes_snaps_verified":False,"scheme_coverage_verified":False,
      "officiating_verified":False,"weather_verified":False,
      "position_rate_is_not_coverage_or_efficiency":True}
    report["phase27_is_challenger_only"]=True
    report["qualified_bets"]=0
    return report

def backtest(history,schedule,first=4,last=18):
    stats=normalize(history); games=team_games(stats)
    completed=completed_weeks(schedule,min(last+1,19),"2099-01-01T00:00:00Z",2026)
    rows=[]
    for week in range(max(first,4),min(last,18)+1):
        if week not in completed or week-1 not in completed:continue
        allowed={x for x in completed if x<week}
        prior=stats[(stats.season==2025)|((stats.season==2026)&stats.week.isin(allowed))]
        actual=stats[(stats.season==2026)&(stats.week==week)]
        contests=schedule[(schedule.season==2026)&(schedule.week==week)&(schedule.game_type=="REG")]
        for g in contests.itertuples():
            home,away=str(g.home_team),str(g.away_team)
            try:volume=opportunity_forecast(games,schedule,home,away,allowed)
            except ValueError:continue
            for club,opp in ((home,away),(away,home)):
                try:pred=role_forecast(prior,volume[club]["pass_attempts"]["projection"],allowed,club)
                except ValueError:continue
                truths=actual[actual.team_code==club].set_index("player_id")
                for p in pred:
                    factor,_,_=position_multiplier(prior,schedule,opp,allowed,
                        str(prior[(prior.season==2026)&(prior.player_id==p["player_id"])].sort_values("week").iloc[-1].position))
                    for metric in ("targets","receptions","receiving_yards"):
                        real=float(truths.loc[p["player_id"],metric]) if p["player_id"] in truths.index else 0.
                        base=float(p[metric])
                        rows.append({"week":week,"metric":metric,"actual":real,
                            "champion":base,"challenger":base*factor,
                            "factor":factor})
    if not rows:raise ValueError("No scored opponent-context comparisons")
    metrics=[]
    for metric in ("targets","receptions","receiving_yards"):
        v=[r for r in rows if r["metric"]==metric]
        a=float(np.mean([abs(r["champion"]-r["actual"]) for r in v]))
        b=float(np.mean([abs(r["challenger"]-r["actual"]) for r in v]))
        metrics.append({"market":metric,"n":len(v),"phase23_mae":round(a,3),
          "phase27_mae":round(b,3),"improved":b<a,
          "adjusted_cases":sum(abs(x["factor"]-1)>1e-5 for x in v)})
    improved=all(x["improved"] for x in metrics)
    return {"version":VERSION,"scored_weeks":sorted(set(r["week"] for r in rows)),
       "metrics":metrics,"player_games":len(rows)//3,
       "phase27_passes_historical_gate":improved,
       "promotion_to_production":False,
       "official_injuries_and_lineup_verified":False,
       "qualified_bets":0}

def markdown(report,audit=None):
    e=report["game"]
    lines=["# GRIDIRON Phase 27 — Matchup context challenger","",
      f"**{e['away']} @ {e['home']} · Week {e['week']} · {e['gameday']}**",
      "**Research only — no verified injuries, official actives, routes, coverage, weather or odds.**","",
      "## Verifiable schedule context","",
      f"- Home: {e['home']}",
      f"- Days since prior game: {e['home']} {report['context']['rest_days_since_prior_game'][e['home']]}, {e['away']} {report['context']['rest_days_since_prior_game'][e['away']]}",
      "Rest shown for context; it is **not yet a validated projection adjustment**.","",
      "## Player receiving forecasts (comparison)","",
      "| Player | Team | Position | Phase 26 rec yards | Phase 27 challenger | Opponent-target factor |",
      "|:--|:--|:--|--:|--:|--:|"]
    for p in report["player_forecasts"][:24]:
        lines.append(f"| {p['player']} | {p['team']} | {p['position']} | {p['phase26_receiving_yards']:.1f} | {p['phase27_challenger_receiving_yards']:.1f} | {p['matchup_adjustment_factor']:.3f} |")
    if audit:
        lines+=["","## Walk-forward accuracy; lower error is better","",
          "| Metric | Player-games | Phase 23 MAE | Phase 27 MAE | Better? |",
          "|:--|--:|--:|--:|:--|"]
        for x in audit["metrics"]:
            lines.append(f"| {x['market']} | {x['n']} | {x['phase23_mae']:.2f} | {x['phase27_mae']:.2f} | {'Yes' if x['improved'] else 'No'} |")
        lines+=["",f"Backtest gate: {'passed' if audit['phase27_passes_historical_gate'] else 'failed'}. **Not promoted to production**."]
    lines+=["","Opponent target rates are prior opposing offenses' **position-level target shares**, not position-specific coverage or efficiency. Do not treat them as player matchup wins.",
       "**Phase 26 projection remains the champion** pending stronger prospective evidence. Zero qualified bets.",""]
    return "\n".join(lines)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--team-a",default="")
    p.add_argument("--team-b",default="")
    p.add_argument("--week",type=int,default=0)
    p.add_argument("--run-backtest",action="store_true")
    p.add_argument("--output",default="output/phase27_matchup_context.json")
    a=p.parse_args()
    folder=Path("private_data");folder.mkdir(exist_ok=True)
    schedule,sha=fetch_schedule(folder)
    frames=[];hashes={"schedule":sha}
    for year in (2025,2026):
        df,meta=download(year,folder);frames.append(df);hashes[str(year)]=meta["sha256"]
    roster,audit=acquire(2026,folder);hashes["roster"]=audit["source_sha256"]
    history=pd.concat(frames,ignore_index=True)
    base=base_board(schedule,history,roster,a.team_a,a.team_b,a.week,source_hashes=hashes)
    report=augment(base,history,schedule,set(base["completed_weeks"]))
    evaluation=backtest(history,schedule) if a.run_backtest else None
    if evaluation:report["heldout_challenger_audit"]=evaluation
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2))
    page=markdown(report,evaluation);print(page)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write(page)
if __name__=="__main__":main()
