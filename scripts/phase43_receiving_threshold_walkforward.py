"""Chronological receiving-threshold diagnostic; never approves wagers."""
import math
import pandas as pd
from scripts.phase43_multimarket_forecasts import prep
from scripts.phase43_receiving_threshold_research import historical_thresholds

def evaluate(raw, *, first_week=4, last_week=8, min_samples=8,
             thresholds=None):
    if not 2<=first_week<=last_week<=18:raise ValueError("Invalid evaluation weeks")
    hist=prep(raw)
    current=hist[(hist.season==2026)&(hist.week.between(first_week,last_week))]
    thresholds=thresholds or {"receptions":(4,5,6),"receiving_yards":(50,70,100)}
    rows=[]
    for actual in current.itertuples(index=False):
        prediction=historical_thresholds(hist,str(actual.player_id),
                  season=2026,week=int(actual.week),
                  thresholds=thresholds,min_samples=min_samples)
        for market,detail in prediction["markets"].items():
            if not detail["sufficient_for_descriptive_review"]:continue
            observed=float(getattr(actual,market))
            if not math.isfinite(observed) or observed<0:continue
            for line,record in detail["thresholds"].items():
                p=record["empirical_hit_rate"]
                if p is None:continue
                outcome=int(observed>=float(line))
                rows.append({"week":int(actual.week),"player_id":str(actual.player_id),
                    "market":market,"threshold":float(line),"sample_size":detail["sample_size"],
                    "empirical_rate":p,"outcome":outcome,
                    "brier":(p-outcome)**2})
    grouped={}
    for market in thresholds:
        for line in thresholds[market]:
            group=[r for r in rows if r["market"]==market and r["threshold"]==float(line)]
            grouped[f"{market}:{line}"]={"scored_observations":len(group),
              "brier_score":round(sum(r["brier"] for r in group)/len(group),6) if group else None,
              "observed_hit_rate":round(sum(r["outcome"] for r in group)/len(group),6) if group else None,
              "mean_empirical_rate":round(sum(r["empirical_rate"] for r in group)/len(group),6) if group else None}
    return {"status":"HISTORICAL_WALK_FORWARD_DIAGNOSTIC_NOT_PROSPECTIVE",
      "first_week":first_week,"last_week":last_week,"min_samples":min_samples,
      "missing_game_rows_not_imputed":True,"calibrated":False,"approved_wagers":0,
      "metrics":grouped,"scored_records":len(rows)}
