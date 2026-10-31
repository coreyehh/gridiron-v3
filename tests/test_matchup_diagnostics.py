import pandas as pd
import pytest
from matchup_engine.diagnostics import paired_diagnostics

def test_diagnostics_rejects_mismatched_games():
    a=pd.DataFrame({"season":[2025],"game_id":["a"]})
    b=pd.DataFrame({"season":[2025],"game_id":["b"]})
    with pytest.raises(ValueError,match="identical games"):
        paired_diagnostics(a,b)

def test_diagnostics_detects_worse_prediction():
    d={"season":[2025],"game_id":["a"],"actual_home_win":[1],
       "actual_margin":[7.],"actual_total":[44.]}
    a=pd.DataFrame(dict(d,home_win_probability=[0.8],pred_margin=[6.],pred_total=[45.]))
    b=pd.DataFrame(dict(d,home_win_probability=[0.5],pred_margin=[0.],pred_total=[50.]))
    r=paired_diagnostics(a,b)
    assert r.delta_brier.iloc[0]>0
    assert r.delta_margin_mae.iloc[0]>0
