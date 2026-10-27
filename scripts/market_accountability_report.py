"""Market-by-market descriptive accountability from verified ledger outcomes.

Only joined, pregame forecasts with externally verified binary outcomes belong
here. ROI is reported only when a captured price and stake are present.
"""
from collections import defaultdict
from math import isfinite
from statistics import mean
from scripts.probability_calibration_audit import evaluate

def report(rows, *, min_sample=10):
    if min_sample<1:raise ValueError("Invalid minimum sample")
    groups=defaultdict(list)
    for r in rows:
        if r.get("result_verified") is not True:
            raise ValueError("All outcomes require external verification")
        groups[str(r["market"])].append(r)
    out={}
    for market,records in sorted(groups.items()):
        n=len(records)
        result={"n":n,"wins":sum(int(r["outcome"]) for r in records),
                "hit_rate":mean(int(r["outcome"]) for r in records),
                "minimum_sample_met":n>=min_sample}
        if n>=min_sample:
            stats=evaluate(records,min_test=min_sample)
            result.update({"brier_score":stats["brier_score"],
                           "log_loss":stats["log_loss"],
                           "calibration_bins":stats["calibration_bins"]})
        else:
            result.update({"brier_score":None,"log_loss":None,
                           "calibration_bins":[]})
        priced=[r for r in records if r.get("decimal_odds") is not None and r.get("stake_units") is not None]
        if len(priced)==n and n:
            profit=0.;risked=0.
            for r in priced:
                odds=float(r["decimal_odds"]);stake=float(r["stake_units"])
                if not (isfinite(odds) and odds>1 and isfinite(stake) and stake>0):
                    raise ValueError("Invalid captured odds or stake")
                risked+=stake
                profit+=stake*(odds-1) if int(r["outcome"])==1 else -stake
            result.update({"realized_profit_units":profit,
                           "realized_roi":profit/risked,"total_staked_units":risked})
        else:
            result.update({"realized_profit_units":None,"realized_roi":None,
                           "total_staked_units":None})
        out[market]=result
    return {"markets":out,"forecast_count":sum(len(g) for g in groups.values()),
            "prospective_validation_certified":False}
