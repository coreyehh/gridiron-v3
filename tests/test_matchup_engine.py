import pandas as pd
import pytest
from matchup_engine.data import load_games
from matchup_engine.features import make_training_frame
from matchup_engine.ratings import prior_team_form

def test_previous_game_only():
    g = pd.DataFrame([
        dict(game_id="g1",gameday=pd.Timestamp("2025-09-01"),home_team="A",away_team="B",home_score=10,away_score=7),
        dict(game_id="g2",gameday=pd.Timestamp("2025-09-08"),home_team="A",away_team="B",home_score=100,away_score=0),
    ])
    form=prior_team_form(g,window=8)
    row=form[(form.team=="A")&(form.gameday==pd.Timestamp("2025-09-08"))].iloc[0]
    assert row.prior_points_for == 10
    assert row.prior_points_against == 7

def test_targets_not_features():
    from matchup_engine.features import FEATURES
    assert not {"margin","total","home_win","home_score","away_score"}.intersection(FEATURES)
