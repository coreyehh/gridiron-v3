import pandas as pd
import pytest
from matchup_engine.paired_accountability import compare_scenario_errors

def test_paired_comparison_uses_same_games():
    data=pd.DataFrame([
      dict(game_id="a",home_score=24.,away_score=17.,
           projected_home_points=27.,projected_away_points=20.,
           scenario_home_points=24.,scenario_away_points=20.,
           personnel_status="MANUAL_SCENARIO_NOT_BACKTESTED"),
      dict(game_id="b",home_score=10.,away_score=10.,
           projected_home_points=20.,projected_away_points=20.,
           scenario_home_points=20.,scenario_away_points=20.,
           personnel_status="NO_VERIFIED_PERSONNEL_OVERLAY")])
    paired,metrics=compare_scenario_errors(data)
    assert len(paired)==1
    assert metrics["paired_games"]==1
    assert metrics["baseline_margin_mae"]==0.
    assert metrics["scenario_margin_mae"]==3.
    assert metrics["margin_mae_improvement"]==-3.

def test_missing_scenarios_not_counted():
    data=pd.DataFrame([dict(game_id="a",home_score=24.,away_score=17.,
           projected_home_points=27.,projected_away_points=20.,
           scenario_home_points=27.,scenario_away_points=20.,
           personnel_status="NO_VERIFIED_PERSONNEL_OVERLAY")])
    _,metrics=compare_scenario_errors(data)
    assert metrics["paired_games"]==0
    assert metrics["margin_mae_improvement"] is None
