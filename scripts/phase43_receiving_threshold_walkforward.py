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
    # Each historical comparison row must itself qualify using only its
    # own earlier player-games. Do not select peers by future workload.
    baseline_hist=hist
    if min_prior_receptions is not None:
        baseline_hist=hist.sort_values(["player_id","season","week"]).copy()
        prior_receipts=pd.to_numeric(baseline_hist["receptions"],errors="coerce")
        baseline_hist["_prior_receptions"]=prior_receipts
        grouped=baseline_hist.groupby("player_id",sort=False)["_prior_receptions"]
        baseline_hist["_prior_volume_mean"]=grouped.transform(
            lambda x: x.shift(1).rolling(5,min_periods=3).mean())
        baseline_hist=baseline_hist[
            baseline_hist["_prior_volume_mean"]>=min_prior_receptions]
    prior_baselines={}
    for wk in range(first_week,last_week+1):
        training=baseline_hist[((baseline_hist.season<2026)|((baseline_hist.season==2026)&(baseline_hist.week<wk))) & (hist.position.isin(("WR","TE","RB"))) ]
        for position in ("WR","TE","RB"):
            position_training=training[training.position==position]
            for market,lines in thresholds.items():
                values=pd.to_numeric(position_training[market],errors="coerce").dropna()
                values=values[values.map(lambda v: math.isfinite(float(v)) and (market=="receiving_yards" or v>=0))]
                for line in lines:
                    prior_baselines[(wk,position,market,float(line))]=(
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
                baseline=prior_baselines[(int(actual.week),str(actual.position),market,float(line))]
                rows.append({"baseline_brier":(baseline-outcome)**2 if baseline is not None else None,
                    "week":int(actual.week),"player_id":str(actual.player_id),
                    "market":market,"threshold":float(line),"sample_size":detail["sample_size"],
                    "empirical_rate":p,"outcome":outcome,
                    "brier":(p-outcome)**2})
    grouped={}
    # Conservative normal-approximation interval on paired per-game Brier differences.
    # Descriptive only: player-games and thresholds are not independent.
    def paired_interval(group):
        diffs=[r["baseline_brier"]-r["brier"] for r in group
               if r["baseline_brier"] is not None]
        n=len(diffs)
        if n<2:return {"paired_n":n,"paired_improvement_ci95":None}
        mean=sum(diffs)/n
        variance=sum((x-mean)**2 for x in diffs)/(n-1)
        half_width=1.96*math.sqrt(variance/n)
        # Six predeclared thresholds: Bonferroni-adjusted familywise 95%
        # normal interval; still descriptive without cluster correction.
        family_z=2.638
        family_half=family_z*math.sqrt(variance/n)
        # Aggregate paired errors by NFL week before uncertainty estimation.
        # This avoids treating same-week player observations as independent.
        week_groups={}
        for row in group:
            if row["baseline_brier"] is not None:
                week_groups.setdefault(row["week"],[]).append(row["baseline_brier"]-row["brier"])
        week_means=[sum(v)/len(v) for v in week_groups.values()]
        week_ci=None
        if len(week_means)>=3:
            week_mean=sum(week_means)/len(week_means)
            week_var=sum((x-week_mean)**2 for x in week_means)/(len(week_means)-1)
            week_half=family_z*math.sqrt(week_var/len(week_means))
            week_ci=[round(week_mean-week_half,6),round(week_mean+week_half,6)]
        return {"paired_n":n,"week_cluster_count":len(week_means),
            "week_cluster_familywise_ci95":week_ci,
            "paired_improvement_familywise_ci95":[round(mean-family_half,6),
                                                    round(mean+family_half,6)],
            "paired_improvement_ci95":[
            round(mean-half_width,6),round(mean+half_width,6)]}
    # Promotion remains blocked even if a small historical slice beats baseline.
    # Paired comparisons use the exact same observed player-games.
    for market in thresholds:
        for line in thresholds[market]:
            group=[r for r in rows if r["market"]==market and r["threshold"]==float(line)]
            grouped[f"{market}:{line}"]={**paired_interval(group),"scored_observations":len(group),
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
      "baseline_cohort":"SAME_POSITION_AND_PRIOR_VOLUME" if min_prior_receptions is not None else "SAME_POSITION_PRIOR_WEEKS",
      "eligible_positions":["WR","TE","RB"],"min_prior_receptions":min_prior_receptions,"missing_game_rows_not_imputed":True,"calibrated":False,"approved_wagers":0,
      "promotion_decision":"NOT_ELIGIBLE_FOR_BETTING_USE",
      "comparison_note":"Paired Brier improvement positive means lower error than historical matched baseline. Normal-approximation intervals, including six-test Bonferroni intervals, are descriptive and do not account for player/game clustering.",
      "metrics":grouped,"scored_records":len(rows)}
