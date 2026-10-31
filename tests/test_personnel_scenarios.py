import pandas as pd
import pytest
from matchup_engine.personnel import apply_personnel_scenarios

def board():
    return pd.DataFrame([dict(game_id="g",home_team="CIN",away_team="PIT",
        projected_home_points=24.,projected_away_points=20.)])

def scenario(**kwargs):
    d=dict(game_id="g",team="CIN",points_adjustment=-3.,
        source="verified team report",observed_at="2026-10-30T14:00:00Z",
        reason="QB unavailable")
    d.update(kwargs)
    return pd.DataFrame([d])

def test_overlay_changes_scenario_not_baseline():
    out=apply_personnel_scenarios(board(),scenario(),"2026-10-31T00:00:00Z")
    assert out.scenario_home_points.iloc[0]==21.
    assert out.projected_home_points.iloc[0]==24.
    assert out.scenario_home_spread.iloc[0]==-1.

def test_rejects_future_dated_report():
    with pytest.raises(ValueError,match="after as-of"):
        apply_personnel_scenarios(board(),scenario(observed_at="2026-11-01T00:00:00Z"),
                                  "2026-10-31T00:00:00Z")

def test_rejects_wrong_team():
    with pytest.raises(ValueError,match="does not participate"):
        apply_personnel_scenarios(board(),scenario(team="NYG"),"2026-10-31T00:00:00Z")
