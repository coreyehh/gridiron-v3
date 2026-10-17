"""Phase 22: leakage-safe game-script challenger and prospective-style residual intervals.

Model uses pregame prior scores as a strength proxy, NOT actual in-game leads.
A historical residual correction is trained on earlier evaluated games only.
Quantile ranges use strictly earlier forecast errors; not player prop probabilities.
"""
import argparse,json,os
from collections import defaultdict
from pathlib import Path
import numpy as np
import pandas as pd
from scripts.ingest import download
from scripts.phase18 import fetch_schedule,completed_weeks
from scripts.phase20_opportunity import team_games,opportunity_forecast,normalize,player_forecast

VERSION="phase22-script-and-interval-prototype"
MIN_CORRECTION=12
MIN_INTERVAL=30
ALPHA=0.20

def team_margins(schedule,team,prior_weeks):
    s=schedule[(schedule.season==2026)&(schedule.game_type=="REG")&
               schedule.week.isin(prior_weeks)&
               ((schedule.home_team==team)|(schedule.away_team==team))]
    margins=[]
    for r in s.itertuples():
        if pd.isna(r.home_score) or pd.isna(r.away_score):continue
        m=float(r.home_score)-float(r.away_score)
        margins.append((int(r.week),m if r.home_team==team else -m))
    return [v for _,v in sorted(margins)[-4:]]

def pregame_state(schedule,home,away,allowed):
    h=team_margins(schedule,home,allowed);a=team_margins(schedule,away,allowed)
    if not h or not a:return {"home":"unknown","away":"unknown","strength_delta":None}
    delta=float(np.mean(h)-np.mean(a))
    label="favored" if delta>=8 else ("underdog" if delta<=-8 else "close")
    reverse={"favored":"underdog","underdog":"favored","close":"close"}[label]
    return {"home":label,"away":reverse,"strength_delta":round(delta,2)}

def corrected(base,kind,metric,history):
    candidates=[r["error"] for r in history if r["state"]==kind and r["metric"]==metric]
    n=len(candidates)
    if n<MIN_CORRECTION:return float(base),0
    # Shrunken prior historical signed residual, bounded to avoid extreme corrections.
    correction=float(np.clip(np.mean(candidates)*n/(n+24),-5,5))
    return max(0.,float(base)+correction),n

def interval(center,metric,residuals,level=0.8):
    vals=[abs(r["error"]) for r in residuals if r["metric"]==metric]
    if len(vals)<MIN_INTERVAL:return None
    # Finite-sample split-conformal-style quantile; evaluated point-by-point pregame.
    arr=np.sort(np.asarray(vals,dtype=float))
    k=min(len(arr),int(np.ceil((len(arr)+1)*level)))
    radius=float(arr[k-1])
    return (max(0.,center-radius),center+radius)

def evaluate(history,schedule,first_week=2,last_week=18):
    frame=normalize(history)
    games=team_games(frame)
    done=set(completed_weeks(schedule,last_week+1,"2099-01-01T00:00:00Z",2026))
    history_residuals=[];rows=[];interval_rows=[]
    for week in range(max(2,first_week),min(18,last_week)+1):
        if week not in done:continue
        allowed={w for w in done if w<week}
        if not allowed or max(allowed)!=week-1:continue
        prior=frame[(frame.season==2025)|((frame.season==2026)&frame.week.isin(allowed))]
        actual_games=games[(games.season==2026)&(games.week==week)]
        schedule_week=schedule[(schedule.season==2026)&(schedule.week==week)&
                               (schedule.game_type=="REG")]
        new_residuals=[]
        for match in schedule_week.itertuples():
            home,away=str(match.home_team),str(match.away_team)
            try:pred=opportunity_forecast(games,schedule,home,away,allowed)
            except ValueError:continue
            state=pregame_state(schedule,home,away,allowed)
            for club in (home,away):
                g=actual_games[actual_games.team_code==club]
                if len(g)!=1:continue
                label=state["home"] if club==home else state["away"]
                for metric in ("pass_attempts","rush_attempts"):
                    baseline=float(pred[club][metric]["projection"])
                    challenger,n=corrected(baseline,label,metric,history_residuals)
                    truth=float(g.iloc[0][metric])
                    conf=interval(challenger,metric,history_residuals)
                    row={"week":week,"team":club,"state":label,"metric":metric,
                         "actual":truth,"phase20":baseline,"phase22":challenger,
                         "correction_training_n":n,"strength_delta":state["strength_delta"],
                         "interval80":list(conf) if conf else None}
                    rows.append(row)
                    if conf:
                        interval_rows.append({"metric":metric,"covered":conf[0]<=truth<=conf[1],
                           "width":conf[1]-conf[0],"week":week})
                    # Score is revealed AFTER predictions; append only after the entire week.
                    new_residuals.append({"state":label,"metric":metric,"error":truth-baseline})
        history_residuals.extend(new_residuals)
    if not rows:raise ValueError("No completed week comparisons")
    summary=[]
    for metric in ("pass_attempts","rush_attempts"):
        seq=[r for r in rows if r["metric"]==metric]
        champ=np.mean([abs(r["actual"]-r["phase20"]) for r in seq])
        challenger=np.mean([abs(r["actual"]-r["phase22"]) for r in seq])
        eligible=[r for r in seq if r["correction_training_n"]>=MIN_CORRECTION]
        summary.append({"metric":metric,"observations":len(seq),
            "phase20_mae":round(float(champ),3),"phase22_mae":round(float(challenger),3),
            "delta":round(float(challenger-champ),3),
            "challenger_eligible_observations":len(eligible),
            "phase22_better":bool(challenger<champ)})
    coverage=[]
    for metric in ("pass_attempts","rush_attempts"):
        s=[r for r in interval_rows if r["metric"]==metric]
        coverage.append({"metric":metric,"n":len(s),"coverage80":round(float(np.mean([r["covered"] for r in s])),3) if s else None,
            "avg_width":round(float(np.mean([r["width"] for r in s])),2) if s else None})
    segment=[]
    for state in ("favored","close","underdog","unknown"):
        s=[r for r in rows if r["state"]==state and r["metric"]=="pass_attempts"]
        if not s:continue
        segment.append({"state":state,"n":len(s),
          "phase20_mae":round(float(np.mean([abs(r["actual"]-r["phase20"]) for r in s])),3),
          "phase22_mae":round(float(np.mean([abs(r["actual"]-r["phase22"]) for r in s])),3)})
    # Deployment remains locked to Phase20 unless BOTH team volume metrics improve
    # and intervals have at least 30 evaluated cases and adequate coverage.
    improved=all(x["phase22_better"] for x in summary)
    enough=all(x["n"]>=30 for x in coverage)
    calibrated=all(x["coverage80"] is not None and 0.72<=x["coverage80"]<=0.88 for x in coverage)
    approved=bool(improved and enough and calibrated)
    return {"model_version":VERSION,"tested_weeks":sorted(set(r["week"] for r in rows)),
      "team_opportunity_rows":len(rows),"accuracy":summary,
      "pregame_strength_segments":segment,"interval80_checks":coverage,
      "phase22_promoted":approved,"production_champion":"phase22" if approved else "phase20",
      "correction_min_prior_samples":MIN_CORRECTION,"interval_min_prior_residuals":MIN_INTERVAL,
      "pre_game_strength_uses_only_prior_final_scores":True,
      "future_week_error_leakage":False,"official_inactives_verified":False,
      "game_state_model":"prior-score-strength proxy; NOT live in-game script",
      "player_roles_or_routes_modeled":False,
      "player_prop_probabilities_calibrated":False,
      "betting_edge_or_roi_verified":False}

def markdown(x):
    lines=["# GRIDIRON Phase 22 — Game-script challenger and interval audit","",
      f"Completed weeks: **{', '.join(map(str,x['tested_weeks']))}** · ",
      f"**Production champion remains: {x['production_champion'].upper()}**","",
      "## Same-game volume accuracy — lower MAE is better","",
      "| Volume | Team-game cases | Phase 20 MAE | Phase 22 MAE | Challenger improves? |",
      "|:--|--:|--:|--:|:--|"]
    for r in x["accuracy"]:
        lines.append(f"| {r['metric']} | {r['observations']} | {r['phase20_mae']:.2f} | {r['phase22_mae']:.2f} | {'Yes' if r['phase22_better'] else 'No'} |")
    lines+=["","## Preliminary 80% prediction-interval checks","",
       "| Metric | Evaluated intervals | Actual coverage | Mean width |",
       "|:--|--:|--:|--:|"]
    for r in x["interval80_checks"]:
        cov=f"{r['coverage80']:.1%}" if r["coverage80"] is not None else "insufficient"
        width=f"{r['avg_width']:.1f}" if r["avg_width"] is not None else "—"
        lines.append(f"| {r['metric']} | {r['n']} | {cov} | {width} |")
    lines+=["","## Prior-score strength segments","",
      "| Pregame state proxy | Team-games | Phase 20 pass MAE | Phase 22 pass MAE |",
      "|:--|--:|--:|--:|"]
    for r in x["pregame_strength_segments"]:
        lines.append(f"| {r['state']} | {r['n']} | {r['phase20_mae']:.2f} | {r['phase22_mae']:.2f} |")
    lines+=["",
      "**Decision:** "+("candidate meets limited internal promotion gates; not validated for bets." if x["phase22_promoted"] else "Do NOT replace Phase 20 yet; the challenger has not met promotion gates."),
      "This is a **pregame prior-score strength proxy** with historical correction, NOT real-time win probability, quarter-by-quarter game-script modeling, or a validated 80%-coverage guarantee.",
      "Only earlier completed weeks contribute residual correction or interval widths. Calibration remains provisional because sample sizes are small and the same dataset informed design.",
      "**No player route/participation inputs or sportsbook win probabilities; zero qualified wagers.**",""]
    return "\n".join(lines)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--first-week",type=int,default=2)
    p.add_argument("--last-week",type=int,default=18)
    p.add_argument("--output",default="output/phase22_diagnostics.json")
    a=p.parse_args()
    if not(2<=a.first_week<=a.last_week<=18):p.error("Need weeks 2..18")
    folder=Path("private_data");folder.mkdir(exist_ok=True)
    schedule,shash=fetch_schedule(folder)
    frames=[];source={"schedule_sha256":shash}
    for year in (2025,2026):
        df,meta=download(year,folder);frames.append(df);source[str(year)+"_sha256"]=meta["sha256"]
    result=evaluate(pd.concat(frames,ignore_index=True),schedule,a.first_week,a.last_week)
    result["sources"]=source
    path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2))
    board=markdown(result);print(board)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as file:file.write(board)
if __name__=="__main__":main()
