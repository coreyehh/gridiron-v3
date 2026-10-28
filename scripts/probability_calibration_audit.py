"""Leakage-aware, chronological evaluation of binary probability forecasts.

Input records are pregame forecasts with known outcomes. This module does not
train a model, assert calibration, or create live wagering recommendations.
"""
from datetime import datetime,timezone
from math import isfinite
from statistics import mean

def _date(value):
    d=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if d.tzinfo is None:raise ValueError("Timezone-aware timestamp required")
    return d.astimezone(timezone.utc)

def evaluate(rows, *, min_test=10, bins=10):
    if bins<2 or min_test<1:raise ValueError("Invalid evaluation settings")
    records=[]
    seen=set()
    for r in rows:
        key=(str(r["fixture_id"]),str(r["market"]),str(r["selection"]),str(r["player_id"]))
        if key in seen:raise ValueError("Duplicate forecast identity")
        seen.add(key)
        p=float(r["probability"])
        y=int(r["outcome"])
        if not isfinite(p) or not 0<=p<=1 or y not in (0,1):
            raise ValueError("Invalid probability or binary outcome")
        made=_date(r["forecast_at_utc"])
        kickoff=_date(r["kickoff_utc"])
        if made>=kickoff:raise ValueError("Post-kickoff forecast leakage")
        records.append((kickoff,key,p,y))
    records.sort(key=lambda x:(x[0],x[1]))
    if len(records)<min_test:raise ValueError("Insufficient evaluation records")
    # Report calibration descriptively; never fit and test on same observations.
    brier=mean((p-y)**2 for _,_,p,y in records)
    logloss=mean(-(y*__import__("math").log(max(p,1e-12))+
                   (1-y)*__import__("math").log(max(1-p,1e-12))) for _,_,p,y in records)
    grouped=[[] for _ in range(bins)]
    for _,_,p,y in records:grouped[min(int(p*bins),bins-1)].append((p,y))
    calibration=[{"lower":i/bins,"upper":(i+1)/bins,"count":len(g),
                  "mean_predicted":mean(p for p,y in g) if g else None,
                  "observed_rate":mean(y for p,y in g) if g else None}
                 for i,g in enumerate(grouped)]
    return {"n":len(records),"brier_score":brier,"log_loss":logloss,
            "calibration_bins":calibration,"evaluated_on_historical_outcomes":True,
            "out_of_sample_certified":False,"live_probability_calibrated":False}

def chronological_split(rows, *, test_fraction=.25):
    if not 0<test_fraction<1:raise ValueError("Invalid test fraction")
    ordered=sorted(rows,key=lambda r:(_date(r["kickoff_utc"]),str(r["fixture_id"])))
    if len(ordered)<2:raise ValueError("Insufficient observations")
    cut=max(1,min(len(ordered)-1,int(len(ordered)*(1-test_fraction))))
    # Do not put games sharing kickoff in both partitions.
    boundary=_date(ordered[cut]["kickoff_utc"])
    train=[r for r in ordered if _date(r["kickoff_utc"])<boundary]
    test=[r for r in ordered if _date(r["kickoff_utc"])>=boundary]
    if not train or not test:raise ValueError("Cannot split kickoff cohort without leakage")
    return train,test
