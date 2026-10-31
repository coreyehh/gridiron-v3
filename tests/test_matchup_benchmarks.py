import pandas as pd
import pytest
from matchup_engine.benchmarks import evaluate_reference

def test_reference_requires_predeclared_total():
    frame=pd.DataFrame({"actual_home_win":[0,1],"actual_margin":[-7,3],"actual_total":[40,50]})
    with pytest.raises(ValueError):
        evaluate_reference(frame)

def test_reference_fixed_probability():
    frame=pd.DataFrame({"actual_home_win":[0,1],"actual_margin":[-7,3],"actual_total":[40,50]})
    scores=evaluate_reference(frame,total=44)
    assert scores["brier"] == pytest.approx(0.25)
    assert scores["games"] == 2
