"""Chronological receiving-threshold diagnostic; never approves wagers."""
import math
import pandas as pd
from scripts.phase43_multimarket_forecasts import prep
from scripts.phase43_receiving_threshold_research import historical_thresholds

def evaluate(raw, *, first_week=4, last_week=8, min_samples=8,
             thresholds=None, min_prior_receptions=None):
    if not 2<=first_week<=last_week<=18:raise ValueError("Invalid evaluation weeks")
    hist=prep(raw)
    current=hist[(hist.season==2026)&(hist.week.between(first_week,last_week)) & (hist.position.isin(("WR","TE","RB")))]
    thresholds=thresholds or {"receptions":(4,5,6),"receiving_yards":(50,70,100)}
    if min_prior_receptions is not None and min_prior_receptions<0:raise ValueError("Invalid volume floor")
    rows=[]
    prior_baselines={}
    for wk in range(first_week,last_week+1):
        training=hist[((hist.season<2026)|((hist.season==2026)&(hist.week<wk))) & (hist.position.isin(("WR","TE","RB"))) ]
        for market,lines in thresholds.items():
            values=pd.to_numeric(training[market],errors="coerce").dropna()
            for line in lines:
                prior_baselines[(wk,market,float(line))]=(
                    float((values>=line).mean()) if len(values) else None)
    for actual in current.itertuples(index=False):
        if min_prior_receptions is not None:
            prior=hist[(hist.player_id.astype(str)==str(actual.player_id)) &
              ((hist.season<2026)|((hist.season==2026)&(hist.week<int(actual.week))))]
            prior_values=pd.to_numeric(prior.sort_values(["season","week"]).tail(5)["receptions"],errors="coerce").dropna()
            if len(prior_values)<3 or float(prior_values.mean())<min_prior_receptions:
                continue
        prediction=historical_thresholds(hist,str(actual.player_id),
                  season=2026,week=int(actual.week),
                  thresholds=thresholds,min_samples=min_samples)
        for market,detail in prediction["markets"].items():
            if not detail["sufficient_for_descriptive_review"]:continue
            observed=float(getattr(actual,market))
            if not math.isfinite(observed) or (market=="receptions" and observed<0):continue
            for line,record in detail["thresholds"].items():
                p=record["empirical_hit_rate"]
                if p is None:continue
                outcome=int(observed>=float(line))
                baseline=prior_baselines[(int(actual.week),market,float(line))]
                rows.append({"baseline_brier":(baseline-outcome)**2 if baseline is not None else None,
                    "week":int(actual.week),"player_id":str(actual.player_id),
                    "market":market,"threshold":float(line),"sample_size":detail["sample_size"],
                    "empirical_rate":p,"outcome":outcome,
                    "brier":(p-outcome)**2})
    grouped={}
    # Promotion remains blocked even if a small historical slice beats baseline.
    # Paired comparisons use the exact same observed player-games.
    for market in thresholds:
        for line in thresholds[market]:
            group=[r for r in rows if r["market"]==market and r["threshold"]==float(line)]
            grouped[f"{market}:{line}"]={"scored_observations":len(group),
              "brier_score":round(sum(r["brier"] for r in group)/len(group),6) if group else None,
              "paired_brier_improvement":round(
                sum(r["baseline_brier"]-r["brier"] for r in group
                    if r["baseline_brier"] is not None)/
                len([r for r in group if r["baseline_brier"] is not None]),6)
                if any(r["baseline_brier"] is not None for r in group) else None,
              "baseline_brier_score":round(
                sum(r["baseline_brier"] for r in group if r["baseline_brier"] is not None)/
                len([r for r in group if r["baseline_brier"] is not None]),6)
                if any(r["baseline_brier"] is not None for r in group) else None,
              "observed_hit_rate":round(sum(r["outcome"] for r in group)/len(group),6) if group else None,
              "mean_empirical_rate":round(sum(r["empirical_rate"] for r in group)/len(group),6) if group else None}
    return {"status":"HISTORICAL_WALK_FORWARD_DIAGNOSTIC_NOT_PROSPECTIVE",
      "first_week":first_week,"last_week":last_week,"min_samples":min_samples,
      "eligible_positions":["WR","TE","RB"],"min_prior_receptions":min_prior_receptions,"missing_game_rows_not_imputed":True,"calibrated":False,"approved_wagers":0,
      "promotion_decision":"NOT_ELIGIBLE_FOR_BETTING_USE",
      "comparison_note":"Paired Brier improvement positive means lower error than prior-week league baseline.",
      "metrics":grouped,"scored_records":len(rows)}
