"""Phase 33: probability and game-day eligibility evidence, research-only.

Use prior-week residuals, avoid missing box rows labelled as zeros, report
prequential probability performance at independently specified thresholds.
Authentic sportsbook line-specific calibration is NOT demonstrated without
point-in-time player-level archived offers. Do not guess official actives.
"""
import argparse,json,math,os
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
from scripts.ingest import download
from scripts.phase18 import fetch_schedule,completed_weeks
from scripts.phase20_opportunity import normalize,team_games
from scripts.phase24_participation_calibration import candidate_predictions,LEVELS
from scripts.phase31_accountability import verify_snapshot

VERSION="phase33-prequential-probability-and-availability-gate-v1"
MIN_RESIDUALS=100
MIN_INDEPENDENT_WEEKS=6
MIN_PROB_CASES=500
BINS=((0,.2),(.2,.4),(.4,.6),(.6,.8),(.8,1.000001))

def residual_probability(errors,center,threshold):
    """Pre-event estimate at an arbitrary numeric threshold, not claimed calibrated."""
    if isinstance(threshold,bool) or not math.isfinite(float(threshold)) or float(threshold)<0:
        raise ValueError("Invalid threshold")
    if not math.isfinite(float(center)) or float(center)<0:
        raise ValueError("Invalid projection")
    if len(errors)<MIN_RESIDUALS:return None
    a=np.asarray(errors,dtype=float)
    if not np.isfinite(a).all():raise ValueError("Nonfinite residual")
    hits=int((a+float(center)>float(threshold)).sum())
    p=(hits+1)/(len(a)+2)
    # Wilson interval is parameter uncertainty for the *frequency estimate*,
    # NOT a complete uncertainty interval for a player's game outcome.
    z=1.96;n=len(a);ph=hits/n
    den=1+z*z/n
    mid=(ph+z*z/(2*n))/den
    half=z*math.sqrt(ph*(1-ph)/n+z*z/(4*n*n))/den
    return {"p_over":round(float(p),6),
        "sampling_interval_95pct":[round(max(0,mid-half),6),
                                   round(min(1,mid+half),6)],
        "residual_n":n,
        "uncertainty_scope":"binomial sampling only; ignores player/game dependence",
        "calibrated_to_offered_lines":False}

def official_availability_gate(evidence=None,locked_at=None,event_kickoff=None):
    """Do not accept a user-supplied True alone as official confirmation.

    A real official-gameday feed must first be integrated, source-verified and
    checked against the exact fixture, player and time; none exists yet.
    """
    return {"official_source_integrated":False,
       "player_game_status":"UNKNOWN",
       "official_active_verified":False,
       "route_assignment_verified":False,
       "eligible":False,
       "reasons":["no_authenticated_official_game_day_player_status_feed",
                  "no_verified_player_route_participation",
                  "no_actual_line_specific_prospective_calibration"]}

def prequential(history,schedule,first_week=4,last_week=18):
    """Freeze each week's residual bank until ALL predictions for week scored.

    Missing player-week stat rows are unresolved and excluded, not assigned
    invented zeros. Individual player independence is NOT assumed.
    """
    stats=normalize(history)
    games=team_games(stats)
    done=set(completed_weeks(schedule,min(last_week+1,19),
         "2099-01-01T00:00:00Z",2026))
    errors=defaultdict(list)
    records=[]
    seen_weeks=[]
    missing=0
    total=0
    for week in range(max(4,first_week),min(last_week,18)+1):
        if week not in done or week-1 not in done:continue
        allowed={w for w in done if w<week}
        before=stats[(stats.season==2025)|((stats.season==2026)&stats.week.isin(allowed))]
        actual=stats[(stats.season==2026)&(stats.week==week)]
        games_w=schedule[(schedule.season==2026)&(schedule.week==week)&
                         (schedule.game_type=="REG")]
        pending=[]
        for game in games_w.itertuples():
            try:
                predictions=candidate_predictions(before,games,schedule,week,
                    str(game.home_team),str(game.away_team),allowed)
            except ValueError:continue
            for (team,pid),metric_centers in predictions.items():
                total+=1
                truth=actual[(actual.team_code==team)&(actual.player_id==pid)]
                if len(truth)!=1:
                    missing+=1;continue
                observed=truth.iloc[0]
                for metric,center in metric_centers.items():
                    value=float(observed[metric])
                    # Predictions for entire week are evaluated on an
                    # unmodified bank, with additions delayed to week end.
                    for line in LEVELS[metric]:
                        result=residual_probability(errors[metric],center,line)
                        if result is None:continue
                        records.append({"week":week,"metric":metric,"threshold":line,
                          "p":result["p_over"],"outcome":int(value>line),
                          "residual_n":result["residual_n"]})
                    pending.append((metric,value-float(center)))
        for metric,error in pending:errors[metric].append(error)
        seen_weeks.append(week)
    scores={}
    for metric in LEVELS:
        subset=[r for r in records if r["metric"]==metric]
        if not subset:
            scores[metric]={"cases":0,"weeks":[],"brier":None,
              "ece":None,"observed_base_rate_brier":None}
            continue
        probs=np.array([x["p"] for x in subset])
        labels=np.array([x["outcome"] for x in subset])
        brier=float(np.mean((probs-labels)**2))
        prior=float(labels.mean())
        reference=float(np.mean((prior-labels)**2))
        bins=[]
        for lo,hi in BINS:
            mask=(probs>=lo)&(probs<hi)
            if not mask.any():continue
            bins.append({"lower":lo,"upper":min(hi,1.),"n":int(mask.sum()),
              "p_mean":round(float(probs[mask].mean()),4),
              "observed":round(float(labels[mask].mean()),4)})
        ece=sum(b["n"]/len(subset)*abs(b["p_mean"]-b["observed"]) for b in bins)
        scores[metric]={"cases":len(subset),
          "weeks":sorted({r["week"] for r in subset}),
          "brier":round(brier,5),"ece":round(ece,5),
          "observed_base_rate_brier":round(reference,5),
          "bins":bins,
          "unconditional_baseline_is_in_sample_diagnostic_only":True}
    research_gate=all(scores[m]["cases"]>=MIN_PROB_CASES and
        len(scores[m]["weeks"])>=MIN_INDEPENDENT_WEEKS and
        scores[m]["brier"]<scores[m]["observed_base_rate_brier"]
        for m in LEVELS)
    return {"version":VERSION,"evaluated_completed_weeks":seen_weeks,
      "player_game_candidates":total,"observed_player_games":total-missing,
      "missing_box_rows_excluded":missing,"scores":scores,
      "research_sample_sufficiency_gate":research_gate,
      "all_lines_illustrative":True,
      "matched_actual_bookmaker_line_calibration_proven":False,
      "independently_validated_prospective_calibration":False,
      "official_availability":official_availability_gate(),
      "qualified_bets":0}

def frozen_threshold_audit(snapshot,errors_by_market,thresholds):
    """No book quotes, no odds calls; user-defined research thresholds.

    Frozen Week6 projections may be used to *illustrate* frequencies, but
    cannot be called calibrated player bets.
    """
    verify_snapshot(snapshot)
    counts={"player_forecasts":len(snapshot["forecasts"]),
            "threshold_comparisons":0,"insufficient_residual_history":0,
            "nominal_frequency_estimates":0,"availability_verified":0}
    for p in snapshot["forecasts"]:
        for market,threshold in thresholds.items():
            if market not in ("receptions","receiving_yards"):continue
            evidence=residual_probability(errors_by_market.get(market,[]),
                      p[market],threshold)
            counts["threshold_comparisons"]+=1
            if evidence is None:counts["insufficient_residual_history"]+=1
            else:counts["nominal_frequency_estimates"]+=1
    return {"status":"illustrative_threshold_check",
        "counts":counts,"sportsbook_lines_provided":False,
        "calibrated_real_market_probabilities":False,
        "eligible_bets":0}

def markdown(report):
    lines=["# GRIDIRON Phase 33 — Probability and official availability evidence","",
      f"Historical completed weeks: {report['evaluated_completed_weeks']}",
      f"Player-game samples with observed box rows: {report['observed_player_games']}",
      f"Missing player boxes excluded (NOT known inactive): {report['missing_box_rows_excluded']}","",
      "## Chronological illustrative-threshold audit (not actual sportsbook lines)","",
      "| Market | Evaluations | Weeks scored | Brier | ECE |",
      "|:--|--:|--:|--:|--:|"]
    for metric,value in report["scores"].items():
        fmt=lambda x:"insufficient" if x is None else f"{x:.4f}"
        lines.append(f"| {metric} | {value['cases']} | {len(value['weeks'])} | {fmt(value['brier'])} | {fmt(value['ece'])} |")
    lines+=["",f"**Research sample-sufficiency gate:** {'PASS' if report['research_sample_sufficiency_gate'] else 'FAIL'}",
      "**Real sportsbook-line calibration:** NOT VERIFIED.",
      "**Official game-day status and routes:** NOT VERIFIED.",
      "**Official betting selections qualified:** 0.",
      "Historical week-by-week evaluation cannot substitute for independent, actual-offer prospective validation. No bookmaker API credits used.",""]
    return "\n".join(lines)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--first-week",type=int,default=4)
    p.add_argument("--last-week",type=int,default=18)
    p.add_argument("--output",default="output/phase33_probability_evidence.json")
    a=p.parse_args()
    if not 4<=a.first_week<=a.last_week<=18:p.error("Weeks 4–18 required")
    folder=Path("private_data");folder.mkdir(exist_ok=True)
    schedule,sh=fetch_schedule(folder)
    chunks=[];hashes={"schedule":sh}
    for season in (2025,2026):
        data,meta=download(season,folder)
        chunks.append(data);hashes[str(season)]=meta["sha256"]
    result=prequential(pd.concat(chunks,ignore_index=True),schedule,a.first_week,a.last_week)
    result["source_sha256"]=hashes
    path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2))
    msg=markdown(result);print(msg)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write(msg)
if __name__=="__main__":main()
