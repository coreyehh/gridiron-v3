"""GRIDIRON Phase 30: shared-cohort player-model tournament.

All forecasts use completed earlier games. Report paired MAE, week-by-week
performance, and prospective-readiness gates. An observational two-week
historical gain never authorizes production promotion or betting picks.
"""
import argparse,json,os
from collections import defaultdict,Counter
from pathlib import Path
import numpy as np
import pandas as pd
from scripts.ingest import download
from scripts.phase18 import fetch_schedule,completed_weeks
from scripts.phase15 import acquire
from scripts.phase20_opportunity import normalize,team_games,opportunity_forecast,player_forecast
from scripts.phase23_role_model import role_forecast
from scripts.phase27_matchup_context import position_multiplier
from scripts.phase28_snap_participation import download_snaps,conservative_join,prior_snap_factor
from scripts.phase29_route_readiness import density_factor

VERSION="phase30-shared-cohort-evidence-leaderboard-v1"
METRICS=("targets","receptions","receiving_yards")
CANDIDATES=("phase20","phase23","phase27","phase28","phase29")
MIN_PROMOTION_WEEKS=6
MIN_PROMOTION_PLAYER_GAMES=1500
MIN_IMPROVEMENT=0.01
MIN_WEEK_WIN_FRACTION=.60

def eligible_for_promotion(audit,baseline="phase23"):
    """One fixed, conservative rule; no tuning on evaluated weeks.

    A backtest gate passing is NOT prospective qualification. The code
    intentionally keeps auto-promotion off even after this evidence gate.
    """
    if audit["player_games"]<MIN_PROMOTION_PLAYER_GAMES or len(audit["weeks"])<MIN_PROMOTION_WEEKS:
        return False,"insufficient_independent_games_or_weeks"
    base={x["metric"]:x for x in audit["summary"][baseline]}
    for metric in METRICS:
        match=base[metric]
        challenger=next(x for x in audit["summary"][audit["candidate"]]
                       if x["metric"]==metric)
        if match["mae"]<=0:return False,"degenerate_baseline"
        gain=(match["mae"]-challenger["mae"])/match["mae"]
        if gain<MIN_IMPROVEMENT:return False,"insufficient_practical_improvement"
    wins=audit["weekly_diagnostics"][audit["candidate"]]
    if len(wins)<MIN_PROMOTION_WEEKS:return False,"insufficient_week_diagnostics"
    if sum(x["yards_improved"] for x in wins)/len(wins)<MIN_WEEK_WIN_FRACTION:
        return False,"not_consistent_across_weeks"
    return True,"research_backtest_gate_passed_prospective_confirmation_still_required"

def tournament(history,schedule,joined,first=4,last=18):
    frame=normalize(history)
    games=team_games(frame)
    completed=set(completed_weeks(schedule,min(last+1,19),"2099-01-01T00:00:00Z",2026))
    rows=[]
    participation=Counter()
    for week in range(max(4,first),min(18,last)+1):
        if week not in completed or week-1 not in completed:continue
        allowed={w for w in completed if w<week}
        if max(allowed,default=0)!=week-1:continue
        past=frame[(frame.season==2025)|((frame.season==2026)&frame.week.isin(allowed))]
        actual=frame[(frame.season==2026)&(frame.week==week)]
        fixtures=schedule[(schedule.season==2026)&(schedule.week==week)&(schedule.game_type=="REG")]
        for g in fixtures.itertuples():
            home,away=str(g.home_team),str(g.away_team)
            try:volume=opportunity_forecast(games,schedule,home,away,allowed)
            except ValueError:continue
            for club,opp in ((home,away),(away,home)):
                try:
                    base=player_forecast(past,volume[club],allowed,club)
                    challenger=role_forecast(past,volume[club]["pass_attempts"]["projection"],allowed,club)
                except ValueError:continue
                base_map={str(p["player_id"]):p for p in base}
                role_map={str(p["player_id"]):p for p in challenger}
                truth=actual[actual.team_code==club].set_index("player_id")
                # Match the *Phase23 eligible* cohort used in Phases27-29.
                # Phase20's broader Phase23 comparison is separate evidence.
                for pid,role in role_map.items():
                    if pid not in base_map:continue
                    history_position=past[(past.season==2026)&(past.team_code==club)&
                                          (past.player_id==pid)].sort_values("week")
                    if history_position.empty:continue
                    pos=str(history_position.iloc[-1].position)
                    f27,_,_=position_multiplier(past,schedule,opp,allowed,pos)
                    f28,n28,_=prior_snap_factor(joined,club,pid,allowed)
                    f29,n29,_=density_factor(past,joined,club,pid,allowed)
                    participation["forecast_players"]+=1
                    if n28>=2:participation["has_prior_snaps"]+=1
                    if n29>=3:participation["has_prior_density"]+=1
                    presence=pid in truth.index
                    if not presence:participation["missing_game_box_entry"]+=1
                    for metric,old_key in (
                        ("targets","targets_projection"),
                        ("receptions","receptions_projection"),
                        ("receiving_yards","receiving_yards_projection")):
                        observed=float(truth.loc[pid,metric]) if presence else 0.
                        root=float(role[metric])
                        rows.append({"week":week,"metric":metric,"player_id":pid,
                          "actual":observed,"phase20":float(base_map[pid][old_key]),
                          "phase23":root,"phase27":root*f27,
                          "phase28":root*f28,"phase29":root*f29,
                          "seen_in_box":presence})
    if not rows:raise ValueError("No shared-cohort scored player-games")
    weeks=sorted({x["week"] for x in rows})
    summary={}
    for name in CANDIDATES:
        output=[]
        for metric in METRICS:
            sub=[r for r in rows if r["metric"]==metric]
            err=[abs(r[name]-r["actual"]) for r in sub]
            full=float(np.mean(err))
            seen=[abs(r[name]-r["actual"]) for r in sub if r["seen_in_box"]]
            output.append({"metric":metric,"n":len(sub),"mae":round(full,4),
                "in_box_n":len(seen),
                "in_box_mae":round(float(np.mean(seen)),4) if seen else None})
        summary[name]=output
    weekly={}
    for name in CANDIDATES:
        byweek=[]
        for w in weeks:
            matches=[r for r in rows if r["week"]==w and r["metric"]=="receiving_yards"]
            score=lambda who:float(np.mean([abs(x[who]-x["actual"]) for x in matches]))
            byweek.append({"week":w,"n":len(matches),
              "phase23_yards_mae":round(score("phase23"),4),
              "candidate_yards_mae":round(score(name),4),
              "yards_improved":bool(score(name)<score("phase23"))})
        weekly[name]=byweek
    comparisons={}
    for name in CANDIDATES:
        if name=="phase23":continue
        metrics=[]
        for b,c in zip(summary["phase23"],summary[name]):
            change=b["mae"]-c["mae"]
            metrics.append({"metric":b["metric"],"error_reduction":round(change,4),
              "relative_error_reduction_pct":round(change/b["mae"]*100,3) if b["mae"] else None})
        comparisons[name]=metrics
    gates={}
    for name in CANDIDATES:
        if name=="phase23":continue
        evidence={"player_games":len(rows)//3,"weeks":weeks,
            "summary":summary,"weekly_diagnostics":weekly,"candidate":name}
        ok,reason=eligible_for_promotion(evidence)
        gates[name]={"research_evidence_gate":ok,"reason":reason,
          "promoted":False}
    return {"version":VERSION,"weeks":weeks,"player_games":len(rows)//3,
      "same_cohort_for_all_five_candidates":True,
      "player_presence_diagnostics":dict(participation),
      "summary":summary,"relative_to_phase23":comparisons,
      "weekly_diagnostics":weekly,"promotion_gates":gates,
      "core_player_champion":"phase23",
      "production_promotions":0,
      "prospective_independent_validation_completed":False,
      "real_price_probability_calibration_verified":False,
      "sportsbook_ev_or_roi_verified":False,
      "official_actives_verified":False,
      "no_prediction_week_features_used":True,"qualified_bets":0}

def markdown(result):
    lines=["# GRIDIRON Phase 30 — Champion/challenger model audit","",
      "**Champion: Phase 23** · Phase 20 / 27 / 28 / 29 checked on identical player-game rows.",
      f"**Completed 2026 weeks:** {', '.join(map(str,result['weeks']))}; **shared player-games:** {result['player_games']}.","",
      "## Paired forecasting accuracy (MAE; lower is better)","",
      "| Model | Targets | Receptions | Receiving yards |","|:--|--:|--:|--:|"]
    for name in CANDIDATES:
        values=[x["mae"] for x in result["summary"][name]]
        lines.append(f"| {name} | {values[0]:.3f} | {values[1]:.3f} | {values[2]:.3f} |")
    lines+=["","## Promotion requirements and outcomes","",
      f"Minimum evidence: **{MIN_PROMOTION_WEEKS} independent completed weeks**, **{MIN_PROMOTION_PLAYER_GAMES} player-games**, >=**{MIN_IMPROVEMENT:.0%}** gain in all three metrics, >=**{MIN_WEEK_WIN_FRACTION:.0%}** of evaluated weeks with better receiving-yard MAE.",
      "This is a research gate, not an automatic deployment; prospective validation is still required.","",
      "| Challenger | Research evidence gate | Reason | Promoted |","|:--|:--|:--|:--|"]
    for name,g in result["promotion_gates"].items():
        lines.append(f"| {name} | {'Pass' if g['research_evidence_gate'] else 'Fail'} | {g['reason']} | No |")
    counts=result["player_presence_diagnostics"]
    lines+=["","## Data confidence","",
      f"- Player-games missing target-week box-score row: {counts.get('missing_game_box_entry',0)} (NOT confirmed inactive).",
      f"- Snap-history observed: {counts.get('has_prior_snaps',0)} of {result['player_games']}; density-history observed: {counts.get('has_prior_density',0)}.",
      "- Player routes, active status, and bookmaker line-specific calibration are still unverified.",
      "- All results retrospective, same-season walk-forward. Data publication timestamps at prediction time are not independently attested.",
      "- **No sportsbook odds, verified ROI, +EV classification, or betting recommendations.**",
      "**Current champion stays Phase 23; all challengers remain research-only.**",""]
    return "\n".join(lines)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--first-week",type=int,default=4)
    parser.add_argument("--last-week",type=int,default=18)
    parser.add_argument("--output",default="output/phase30_leaderboard.json")
    a=parser.parse_args()
    if not 4<=a.first_week<=a.last_week<=18:parser.error("Weeks 4-18 required")
    folder=Path("private_data");folder.mkdir(exist_ok=True)
    schedule,hash_schedule=fetch_schedule(folder)
    frames=[];hashes={"schedule":hash_schedule}
    for season in (2025,2026):
        f,meta=download(season,folder)
        frames.append(f);hashes[str(season)]=meta["sha256"]
    history=pd.concat(frames,ignore_index=True)
    roster,roster_meta=acquire(2026,folder);hashes["roster"]=roster_meta["source_sha256"]
    snaps,source=download_snaps(2026,folder);hashes["historical_snaps"]=source["sha256"]
    joined=conservative_join(history,snaps,roster)
    result=tournament(history,schedule,joined,a.first_week,a.last_week)
    result["source_sha256"]=hashes
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2))
    page=markdown(result)
    print(page)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write(page)
if __name__=="__main__":main()
