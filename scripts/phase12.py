"""GRIDIRON Phase 12: identity matching + probability diagnostic.

No roster source in this repo proves a 2026 game-day active designation.
Diagnostic thresholds are not historical sportsbook lines.
"""
import argparse, json, math, re, unicodedata
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from scripts.evaluate_eligible import CONFIG, FEATURES

def canonical(name):
    if not isinstance(name,str):return ""
    s=unicodedata.normalize("NFKD",name)
    s="".join(c for c in s if not unicodedata.combining(c))
    s=re.sub(r"[^a-z0-9 ]"," ",s.lower())
    s=re.sub(r"\b(jr|sr|ii|iii|iv)\b","",s)
    return " ".join(s.split())

def match_player(name,team,records,asof_season):
    """Only exact normalized name + explicit team + current-season evidence.

    No fuzzy matches, no cross-season assumption, no name-only join.
    """
    norm=canonical(name)
    if not norm or not team:return {"status":"UNRESOLVED","player_id":None}
    candidates={str(r["player_id"]) for r in records
        if canonical(r.get("player_name"))==norm and r.get("team")==team
        and r.get("season")==asof_season and r.get("player_id")}
    if len(candidates)==1:
        return {"status":"IDENTITY_MATCHED_NOT_ACTIVE_VERIFIED","player_id":next(iter(candidates))}
    return {"status":"AMBIGUOUS" if len(candidates)>1 else "UNRESOLVED","player_id":None}

def empirical_over(mean,line,reference_residuals):
    """Smoothed CDF diagnostic; no automatic live market activation."""
    r=np.asarray(reference_residuals,dtype=float)
    r=r[np.isfinite(r)]
    if len(r)<50:raise ValueError("Need at least 50 validation residuals")
    return float((np.count_nonzero(mean+r>line)+0.5)/(len(r)+1))

def diagnose(features):
    frame=features.copy()
    results=[]
    for pos,market,threshold in CONFIG:
        recent="prior5_"+market
        pool=frame[(frame.prior_position==pos)&(frame.prior_observations>=3)&
                   (frame[recent]>=threshold)&frame[market].notna()].copy()
        train=pool[pool.season.between(2021,2023)]
        val=pool[pool.season.eq(2024)]
        test=pool[pool.season.eq(2025)]
        entry={"position":pos,"market":market,"train_n":int(len(train)),
               "validation_n":int(len(val)),"test_n":int(len(test))}
        if min(len(train),len(val),len(test))<100:
            results.append(dict(entry,status="insufficient_samples"));continue
        # Freeze model using <=2023 training; use 2024 *only* as calibration.
        model=make_pipeline(SimpleImputer(strategy="constant",fill_value=0),
                            StandardScaler(),Ridge(alpha=10.0))
        model.fit(train[FEATURES].fillna(0),train[market])
        pv=np.maximum(0,model.predict(val[FEATURES].fillna(0)))
        pt=np.maximum(0,model.predict(test[FEATURES].fillna(0)))
        residual=(val[market].to_numpy()-pv)
        # The grid comprises synthetic diagnostic thresholds, NOT quoted lines.
        # Defined without looking at 2025 outcomes.
        grid=np.unique(np.maximum(0,np.quantile(pv,[.25,.5,.75])).round(1))
        actual=test[market].to_numpy()
        observations=[]
        for line in grid:
            if market=="receptions":line=float(math.floor(line)+0.5)
            y=(actual>line).astype(float)
            prob=np.array([empirical_over(x,line,residual) for x in pt])
            prior=(val[market].to_numpy()>line).mean()
            brier=float(np.mean((prob-y)**2))
            baseline=float(np.mean((prior-y)**2))
            observations.append({"synthetic_threshold":line,"n":len(test),
               "brier":round(brier,5),"reference_rate_brier":round(baseline,5),
               "mean_probability":round(float(prob.mean()),4),
               "observed_over_rate":round(float(y.mean()),4)})
        results.append(dict(entry,status="diagnostic_only",
            synthetic_thresholds=observations,
            beating_reference_count=sum(x["brier"]<x["reference_rate_brier"] for x in observations),
            threshold_count=len(observations)))
    return {"status":"historical_probability_diagnostic_not_bookmaker_calibration",
      "created_at_utc":datetime.now(timezone.utc).isoformat(),
      "training_seasons":[2021,2022,2023],"calibration_season":2024,
      "untouched_test_season":2025,"betting_probability_approved":False,
      "historical_bookmaker_lines_available":False,"historical_offered_player_universe_verified":False,
      "2026_player_roster_verified":False,"roi_verified":False,
      "limitations":["Thresholds are synthetic, not historical bookmaker offerings",
       "2025 population drawn from observed postgame statistics",
       "No reliable NFL 2026 gameday active roster crosswalk",
       "Residual-calibration diagnostic is not a live-edge authorization"],
      "results":results}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--features",default="output/features.csv")
    p.add_argument("--output",default="output/phase12_diagnostic.json")
    a=p.parse_args()
    report=diagnose(pd.read_csv(a.features))
    f=Path(a.output);f.parent.mkdir(parents=True,exist_ok=True)
    f.write_text(json.dumps(report,indent=2))
    print(json.dumps({"status":report["status"],
        "markets_tested":len(report["results"]),
        "betting_probability_approved":False,"roi_verified":False},indent=2))
if __name__=="__main__":main()
