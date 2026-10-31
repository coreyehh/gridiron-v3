"""Paired baseline vs personnel-scenario error, on identical completed games.

Do not imply scenario win probabilities: only point projections are adjusted.
"""
import pandas as pd

def compare_scenario_errors(graded):
    required={"game_id","home_score","away_score","projected_home_points",
              "projected_away_points","scenario_home_points","scenario_away_points",
              "personnel_status"}
    missing=required-set(graded.columns)
    if missing:
        raise ValueError(f"Missing paired evaluation fields: {sorted(missing)}")
    completed=graded.loc[graded.home_score.notna()&graded.away_score.notna()].copy()
    scenarios=completed.loc[completed.personnel_status.eq("MANUAL_SCENARIO_NOT_BACKTESTED")].copy()
    if scenarios.empty:
        return scenarios,{"paired_games":0,"baseline_margin_mae":None,
                          "scenario_margin_mae":None,"baseline_total_mae":None,
                          "scenario_total_mae":None,"margin_mae_improvement":None,
                          "total_mae_improvement":None}
    actual_margin=scenarios.home_score-scenarios.away_score
    actual_total=scenarios.home_score+scenarios.away_score
    baseline_margin=scenarios.projected_home_points-scenarios.projected_away_points
    scenario_margin=scenarios.scenario_home_points-scenarios.scenario_away_points
    baseline_total=scenarios.projected_home_points+scenarios.projected_away_points
    scenario_total=scenarios.scenario_home_points+scenarios.scenario_away_points
    scenarios["baseline_margin_error"]=(actual_margin-baseline_margin).abs()
    scenarios["scenario_margin_error"]=(actual_margin-scenario_margin).abs()
    scenarios["baseline_total_error"]=(actual_total-baseline_total).abs()
    scenarios["scenario_total_error"]=(actual_total-scenario_total).abs()
    metrics={"paired_games":int(len(scenarios))}
    for label in ["baseline_margin","scenario_margin","baseline_total","scenario_total"]:
        metrics[f"{label}_mae"]=float(scenarios[f"{label}_error"].mean())
    metrics["margin_mae_improvement"]=metrics["baseline_margin_mae"]-metrics["scenario_margin_mae"]
    metrics["total_mae_improvement"]=metrics["baseline_total_mae"]-metrics["scenario_total_mae"]
    return scenarios,metrics
