"""Phase 24: participation evidence gate and prequential player-prop calibration audit.

No official actives, route or coverage feed is bundled. Never infer verified
availability from a roster snapshot or from a missing statistical record.
Use only earlier weeks to calibrate later weeks, and never label artificial
thresholds as offered sportsbook odds or as +EV betting opportunities.
"""
import argparse,json,os
from collections import defaultdict
from pathlib import Path
import numpy as np
import pandas as pd
from scripts.ingest import download
from scripts.phase18 import fetch_schedule,completed_weeks
from scripts.phase20_opportunity import normalize,team_games,opportunity_forecast,player_forecast
from scripts.phase23_role_model import role_forecast

VERSION="phase24-honest-availability-and-prequential-calibration-v1"
MIN_HISTORY=50
LEVELS={"receptions":(1.5,2.5,3.5,4.5,5.5),
        "receiving_yards":(24.5,39.5,54.5,69.5,84.5)}
BINS=((0,.2),(.2,.4),(.4,.6),(.6,.8),(.8,1.000001))

def availability_gate(roster,official_actives=None,route_snap_source=None):
    # Caller cannot silently turn roster existence into confirmed availability.
    return {"roster_is_identity_only":True,
      "official_active_data_available":bool(official_actives),
      "routes_snaps_data_available":bool(route_snap_source),
      "game_day_actives_verified":False,"routes_verified":False,
      "bet_eligible":False,
      "reason":"Official game-day active and independently verified participation inputs not integrated"}

def candidate_predictions(prior,games,schedule,week,club_a,club_b,allowed):
    volume=opportunity_forecast(games,schedule,club_a,club_b,allowed)
    result={}
    for club in (club_a,club_b):
        previous=player_forecast(prior,volume[club],allowed,club)
        updated=role_forecast(prior,volume[club]["pass_attempts"]["projection"],allowed,club)
        names={str(p["player_id"]):p for p in previous}
        newer={str(p["player_id"]):p for p in updated}
        for pid,p in names.items():
            challenger=newer.get(pid)
            # Phase23 suppresses stale roles, but not knowing official active
            # status is NOT evidence that a player is inactive.
            result[(club,pid)]={metric:(
                float(challenger[metric]) if challenger else 0.
            ) for metric in LEVELS}
    return result

def empirical_probability(residuals,center,line):
    """Smoothed empirical P(actual > threshold), trained on prior residuals only."""
    if len(residuals)<MIN_HISTORY:return None
    sample=np.asarray(residuals,dtype=float)
    # symmetric Laplace smoothed indicator, avoids unjustified 0%/100%.
    hits=int(np.sum(sample>float(line)-float(center)))
    return (hits+1.)/(len(sample)+2.)

def evaluate(history,schedule,first_week=4,last_week=18):
    frame=normalize(history);games=team_games(frame)
    completed=set(completed_weeks(schedule,min(last_week+1,19),
                                  "2099-01-01T00:00:00Z",2026))
    residuals=defaultdict(list);evaluations=[];weeks=[]
    predicted_rows=0;missing_box=0
    for week in range(max(4,first_week),min(last_week,18)+1):
        if week not in completed or week-1 not in completed:continue
        allowed={w for w in completed if w<week}
        prior=frame[(frame.season==2025)|((frame.season==2026)&frame.week.isin(allowed))]
        actual=frame[(frame.season==2026)&(frame.week==week)]
        matches=schedule[(schedule.season==2026)&(schedule.week==week)&
                         (schedule.game_type=="REG")]
        pending=[];week_samples=0
        for match in matches.itertuples():
            home,away=str(match.home_team),str(match.away_team)
            try:preds=candidate_predictions(prior,games,schedule,week,home,away,allowed)
            except ValueError:continue
            for (club,pid),values in preds.items():
                found=actual[(actual.team_code==club)&(actual.player_id==pid)]
                row=found.iloc[0] if len(found)==1 else None
                if row is None:missing_box+=1
                predicted_rows+=1;week_samples+=1
                for metric,center in values.items():
                    truth=float(row[metric]) if row is not None else 0.
                    history_residuals=residuals[metric]
                    for line in LEVELS[metric]:
                        probability=empirical_probability(history_residuals,center,line)
                        if probability is not None:
                            evaluations.append({"week":week,"metric":metric,
                                 "line":line,"predicted":probability,
                                 "outcome":int(truth>line),
                                 "training_residual_count":len(history_residuals)})
                    pending.append((metric,truth-center))
        # All same-week comparisons must use only past *completed* weeks.
        for market,error in pending:residuals[market].append(error)
        if week_samples:weeks.append(week)
    market_metrics=[]
    for metric in LEVELS:
        cases=[x for x in evaluations if x["metric"]==metric]
        if not cases:
            market_metrics.append({"metric":metric,"n":0,"brier":None,
               "naive_brier":None,"ece":None,"observed_rate":None,
               "bin_results":[]})
            continue
        outcomes=np.asarray([x["outcome"] for x in cases])
        probs=np.asarray([x["predicted"] for x in cases])
        brier=float(np.mean((probs-outcomes)**2))
        # Comparison is a neutral fixed 50/50 reference; not a trained
        # historical unconditional rate or sportsbook implied price.
        naive=float(np.mean((.5-outcomes)**2))
        bins=[]
        for lo,hi in BINS:
            select=(probs>=lo)&(probs<hi)
            if not select.any():continue
            bins.append({"probability_range":[lo,min(hi,1.)],"n":int(select.sum()),
                         "predicted_rate":round(float(probs[select].mean()),4),
                         "observed_rate":round(float(outcomes[select].mean()),4)})
        ece=sum(b["n"]/len(cases)*abs(b["predicted_rate"]-b["observed_rate"]) for b in bins)
        market_metrics.append({"metric":metric,"n":len(cases),
           "brier":round(brier,4),"naive_brier":round(naive,4),
           "ece":round(float(ece),4),
           "observed_rate":round(float(outcomes.mean()),4),
           "bin_results":bins})
    return {"model_version":VERSION,"test_weeks":weeks,
       "player_game_evaluations":predicted_rows,"missing_week_box_rows":missing_box,
       "probability_metrics":market_metrics,
       "all_thresholds_are_illustrative_not_sportsbook_lines":True,
       "same_week_outcomes_excluded_from_probability_training":True,
       "availability":availability_gate([]),
       "not_bet_qualified":True,"official_bets":0,
       "bookmaker_prices_used":False,"sportsbook_ev_verified":False,
       "provider_data_publication_asof_verified":False}

def markdown(report):
    lines=["# GRIDIRON Phase 24 — Participation & probability audit","",
       f"**Completed evaluated weeks:** {', '.join(map(str,report['test_weeks'])) or 'none'}",
       f"**Player-games:** {report['player_game_evaluations']}",
       f"**Player-week rows not present in box feed:** {report['missing_week_box_rows']}",
       "",
       "## Out-of-sample threshold probability accuracy","",
       "| Market | Threshold outcomes scored | Brier (lower better) | Fixed 50% reference | Calibration ECE |",
       "|:--|--:|--:|--:|--:|"]
    for r in report["probability_metrics"]:
        def fmt(x):return "not enough prior data" if x is None else f"{x:.3f}"
        lines.append(f"| {r['metric']} | {r['n']} | {fmt(r['brier'])} | {fmt(r['naive_brier'])} | {fmt(r['ece'])} |")
    lines+=["","## Participation verification gate","",
       "- NFLverse roster snapshots establish identity, NOT game-day availability.",
       "- No verified active/inactive statuses, per-route participation, snap counts, or defensive coverage inputs are integrated.",
       "- These probabilities are tested against **fixed illustrative statistical thresholds**, NOT live sportsbook offers.",
       "- The same completed week is excluded from residual training before its outcomes are graded.",
       "- Do not report a betting edge, qualified picks, or expected ROI from this workflow.",
       ""]
    return "\n".join(lines)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--first-week",type=int,default=4)
    p.add_argument("--last-week",type=int,default=18)
    p.add_argument("--output",default="output/phase24_audit.json")
    a=p.parse_args()
    if not 4<=a.first_week<=a.last_week<=18:p.error("Weeks 4–18 required")
    folder=Path("private_data");folder.mkdir(exist_ok=True)
    schedule,shash=fetch_schedule(folder)
    frames=[];sources={"schedule_sha256":shash}
    for yr in (2025,2026):
        f,meta=download(yr,folder);frames.append(f);sources[str(yr)]=meta["sha256"]
    report=evaluate(pd.concat(frames,ignore_index=True),schedule,a.first_week,a.last_week)
    report["sources"]=sources
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2))
    rendered=markdown(report);print(rendered)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write(rendered)
if __name__=="__main__":main()
