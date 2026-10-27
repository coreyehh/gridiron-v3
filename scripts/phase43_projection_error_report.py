"""Score original Phase43 point projections against separately verified boxes.

Requires explicit verified fixture/player/market result keys. Missing observations
remain missing, never silently converted to zero.
"""
from collections import defaultdict
from math import isfinite,sqrt
from statistics import mean

def evaluate(exported, observations, *, min_sample=10):
    if exported.get("source")!="phase43_original_locked_snapshot":
        raise ValueError("Expected locked Phase43 export")
    if min_sample<1:raise ValueError("Invalid sample threshold")
    lookup={}
    for row in observations:
        key=(str(row["fixture_id"]),str(row["player_id"]),str(row["market"]))
        if key in lookup:raise ValueError("Duplicate observed result")
        if row.get("result_verified") is not True:raise ValueError("Unverified observed result")
        value=float(row["actual"])
        if not isfinite(value) or value<0:raise ValueError("Invalid observed statistic")
        lookup[key]=value
    groups=defaultdict(list)
    missing=0
    for row in exported["projections"]:
        if row.get("line_specific_probability") is not None or row.get("approved_wager") is not False:
            raise ValueError("Point-projection export contains a wager claim")
        key=(str(row["fixture_id"]),str(row["player_id"]),str(row["market"]))
        if key not in lookup:
            missing+=1
            continue
        projection=float(row["point_projection"])
        if not isfinite(projection) or projection<0:raise ValueError("Invalid projection")
        # Probability outputs require a different scoring rule than yard/count
        # projections and must not be treated as measured yardage.
        if row["market"] in ("anytime_touchdown","two_plus_touchdowns","three_plus_touchdowns"):
            continue
        groups[row["market"]].append((projection,lookup[key]))
    metrics={}
    for market,points in sorted(groups.items()):
        errors=[p-a for p,a in points]
        metrics[market]={"observations":len(points),
                         "mae":mean(abs(e) for e in errors),
                         "rmse":sqrt(mean(e*e for e in errors)),
                         "mean_error":mean(errors),
                         "minimum_sample_met":len(points)>=min_sample}
    return {"status":"HISTORICAL_POINT_PROJECTION_DIAGNOSTIC",
            "markets":metrics,"unmatched_projection_count":missing,
            "approved_wagers":0,"calibrated_betting_probabilities":False}
