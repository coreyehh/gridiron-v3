import pandas as pd
import pytest
from matchup_engine.compare import compare_models
from matchup_engine.features import FEATURES
from matchup_engine.epa_features import EPA_FEATURES

def test_comparison_rejects_insufficient_history():
    frame=pd.DataFrame(columns=["season","gameday","game_id","home_win","margin","total"]+FEATURES+EPA_FEATURES)
    with pytest.raises(ValueError):
        compare_models(frame)
