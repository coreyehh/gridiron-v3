"""Phase 13: chronological calibration diagnostic, not an authorized betting model."""
import argparse,json,math
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from scripts.evaluate_eligible import CONFIG,FEATURES

SHIFTS=(-.4,-.3,-.2,-.1,0.,.1,.2)

def tail_probability(prediction,line,residuals):
    r=np.asarray(residuals,dtype=float);r=r[np.isfinite(r)]
    if len(r)<50:raise ValueError("At least 50 earlier residuals required")
    return (np.count_nonzero(prediction+r>line)+.5)/(len(r)+1)

def shift_probability(prob,offset):
    p=np.asarray(prob,dtype=float)
    if not np.isfinite(p).all() or np.any(p<=0) or np.any(p>=1):
        raise ValueError("Invalid probability")
    z=np.log(p/(1-p))
    return 1/(1+np.exp(-np.clip(z+offset,-35,35)))

def brier(y,p):return float(np.mean((np.asarray(y)-np.asarray(p))**2))
def logloss(y,p):
    p=np.clip(np.asarray(p),1e-6,1-1e-6);y=np.asarray(y)
    return float(-np.mean(y*np.log(p)+(1-y)*np.log(1-p)))

def reliability(y,p):
    a=np.asarray(y);p=np.asarray(p);bins=[];ece=0.
    for i in range(5):
        lo,hi=i/5,(i+1)/5
        m=(p>=lo)&((p<hi) if i<4 else (p<=hi))
        if m.any():
            pred=float(p[m].mean());obs=float(a[m].mean())
            ece+=float(m.mean())*abs(pred-obs)
            bins.append({"range":[lo,hi],"n":int(m.sum()),
                         "predicted_over":round(pred,4),"observed_over":round(obs,4)})
    return round(ece,5),bins

def thresholds(predictions,market):
    grid=np.unique(np.maximum(0,np.quantile(predictions,[.25,.5,.75])).round(1))
    if market=="receptions":return sorted({float(math.floor(x)+.5) for x in grid})
    return sorted({float(x) for x in grid})

def calibrate_group(train,validation,test,market):
    early=validation.week<=9;later=~early
    if min(early.sum(),later.sum(),len(test))<50:raise ValueError("Insufficient split samples")
    model=make_pipeline(SimpleImputer(strategy="constant",fill_value=0),StandardScaler(),Ridge(alpha=10.))
    model.fit(train[FEATURES],train[market])
    pv=np.maximum(0,model.predict(validation[FEATURES]))
    pt=np.maximum(0,model.predict(test[FEATURES]))
    yv=validation[market].to_numpy()
    residual_early=yv[early.to_numpy()]-pv[early.to_numpy()]
    residual_all=yv-pv
    grid=thresholds(pv,market)
    tuning=[]
    for line in grid:
        raw=np.array([tail_probability(x,line,residual_early) for x in pv[later.to_numpy()]])
        truth=(yv[later.to_numpy()]>line).astype(float)
        tuning.append((raw,truth))
    scores={s:float(np.mean([brier(truth,shift_probability(raw,s)) for raw,truth in tuning])) for s in SHIFTS}
    picked=min(scores,key=lambda x:(scores[x],abs(x)))
    if scores[picked]>=scores[0.]-1e-5:picked=0.
    locked=picked*.5
    out=[]
    for line in grid:
        actual=(test[market].to_numpy()>line).astype(float)
        raw=np.array([tail_probability(x,line,residual_all) for x in pt])
        adjusted=shift_probability(raw,locked)
        re,rb=reliability(actual,raw);ae,ab=reliability(actual,adjusted)
        out.append({"synthetic_threshold":line,"n":len(actual),
          "raw_brier":round(brier(actual,raw),6),"adjusted_brier":round(brier(actual,adjusted),6),
          "raw_logloss":round(logloss(actual,raw),6),"adjusted_logloss":round(logloss(actual,adjusted),6),
          "raw_ece":re,"adjusted_ece":ae,"raw_mean_probability":round(float(raw.mean()),5),
          "adjusted_mean_probability":round(float(adjusted.mean()),5),
          "observed_over_rate":round(float(actual.mean()),5),
          "raw_reliability_bins":rb,"adjusted_reliability_bins":ab,
          "adjusted_improves_brier":bool(brier(actual,adjusted)<brier(actual,raw))})
    return {"early_2024_n":int(early.sum()),"late_2024_n":int(later.sum()),
        "selected_offset_on_2024":picked,"locked_shrunk_offset":locked,
        "late_2024_brier_zero":round(scores[0.],6),
        "late_2024_brier_selected":round(scores[picked],6),"thresholds":out}

def evaluate(frame):
    results=[]
    for pos,market,threshold in CONFIG:
        prior="prior5_"+market
        pool=frame[(frame.prior_position==pos)&(frame.prior_observations>=3)&
                   (frame[prior]>=threshold)&frame[market].notna()]
        train=pool[pool.season.between(2021,2023)]
        validation=pool[pool.season==2024];test=pool[pool.season==2025]
        entry={"position":pos,"market":market,"train_n":len(train),
               "calibration_n":len(validation),"heldout_n":len(test)}
        if min(len(train),len(validation),len(test))<100:
            results.append(dict(entry,status="insufficient_samples"));continue
        try:measured=calibrate_group(train,validation,test,market)
        except ValueError as exc:
            results.append(dict(entry,status="insufficient_samples",reason=str(exc)));continue
        rows=measured["thresholds"]
        raw=float(np.mean([x["raw_brier"] for x in rows]))
        corrected=float(np.mean([x["adjusted_brier"] for x in rows]))
        results.append(dict(entry,status="evaluated",**measured,
            mean_raw_brier=round(raw,6),mean_adjusted_brier=round(corrected,6),
            calibration_improves_heldout=bool(corrected<raw and measured["locked_shrunk_offset"]!=0)))
    return {"status":"phase13_synthetic_threshold_calibration_diagnostic",
        "created_at_utc":datetime.now(timezone.utc).isoformat(),
        "training_seasons":[2021,2022,2023],
        "early_2024_calibration_weeks":"1-9","late_2024_tuning_weeks":"10+",
        "holdout_season":2025,
        "method":"2024 second-half tuned logit offset, shrunk by half; both 2025 variants use full 2024 residual CDF",
        "synthetic_thresholds_only":True,"historical_bookmaker_prices_available":False,
        "offered_player_universe_verified":False,"player_identity_2026_verified":False,
        "betting_probability_approved":False,"roi_verified":False,"results":results}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--features",default="output/features.csv")
    p.add_argument("--output",default="output/phase13_diagnostic.json")
    a=p.parse_args();r=evaluate(pd.read_csv(a.features))
    dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(r,indent=2))
    print(json.dumps({"status":r["status"],"evaluated_markets":sum(x["status"]=="evaluated" for x in r["results"]),
       "markets_improved":sum(x.get("calibration_improves_heldout",False) for x in r["results"]),
       "betting_probability_approved":False},indent=2))
if __name__=="__main__":main()
