"""Research-only historical threshold frequencies for Phase43 receiving markets.

This is an empirical descriptive distribution, NOT a validated betting model.
Missing player-week rows are never imputed as zero. No bookmaker inputs.
"""
import math
import pandas as pd
from scripts.phase43_multimarket_forecasts import prep

MARKETS=("receptions","receiving_yards")

def historical_thresholds(raw, player_id, *, season, week, thresholds=None, min_samples=8):
    if min_samples<3:raise ValueError("min_samples must be at least 3")
    if season!=2026 or not 1<=week<=18:raise ValueError("Unsupported target period")
    hist=prep(raw)
    prior=hist[(hist.player_id.astype(str)==str(player_id))&
       ((hist.season<season)|((hist.season==season)&(hist.week<week)))].copy()
    prior=prior.sort_values(["season","week"])
    thresholds=thresholds or {"receptions":(3,4,5,6,7,8),
                              "receiving_yards":(40,50,60,70,80,100)}
    if set(thresholds)-set(MARKETS):raise ValueError("Unsupported market")
    out={}
    for market,lines in thresholds.items():
        numeric=pd.to_numeric(prior[market],errors="coerce")
        invalid=numeric.notna() & (~numeric.map(lambda x: math.isfinite(float(x)) and (market=="receiving_yards" or float(x)>=0) if pd.notna(x) else True))
        values=numeric.loc[numeric.notna() & ~invalid]
        quarantined=int(invalid.sum())
        count=len(values)
        if len(set(float(x) for x in lines))!=len(lines):raise ValueError("Duplicate threshold")
        probabilities={}
        for line in lines:
            if not isinstance(line,(int,float)) or not math.isfinite(line) or line<0:
                raise ValueError("Invalid threshold")
            hits=int((values>=line).sum())
            probabilities[str(line)]={"observed_hits":hits,
                 "observed_games":count,
                 "empirical_hit_rate":round(hits/count,6) if count else None}
        out[market]={"sample_size":count,"sufficient_for_descriptive_review":count>=min_samples,
            "invalid_historical_rows_quarantined":quarantined,
            "missing_market_values_excluded":int(numeric.isna().sum()),
            "thresholds":probabilities}
    return {"player_id":str(player_id),"target_season":season,"target_week":week,
        "status":"RESEARCH_ONLY_UNCALIBRATED_HISTORICAL_FREQUENCIES",
        "absent_game_rows_imputed":False,"opponent_adjusted":False,
        "role_verified":False,"calibrated":False,"approved_wagers":0,
        "markets":out}
