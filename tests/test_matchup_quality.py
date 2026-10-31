import pandas as pd
import pytest
from matchup_engine.quality import validate_prediction_board

def fixture():
    board=pd.DataFrame([dict(game_id="x",season=2026,week=8,gameday="2026-11-01",
      home_win_probability=.6,away_win_probability=.4,
      projected_home_points=24.,projected_away_points=20.,
      pred_total=44.,fair_home_spread=-4.)])
    schedule=pd.DataFrame([dict(game_id="old",season=2026,week=7,game_type="REG",gameday="2026-10-25",home_score=20.,away_score=17.),
                           dict(game_id="x",season=2026,week=8,game_type="REG",gameday="2026-11-01",home_score=None,away_score=None)])
    return board,schedule

def test_valid_board():
    board,schedule=fixture()
    assert validate_prediction_board(board,schedule,"2026-10-31")["games"]==1

def test_rejects_inconsistent_spread():
    board,schedule=fixture()
    board.loc[0,"fair_home_spread"]=4.
    with pytest.raises(ValueError,match="fair spreads"):
        validate_prediction_board(board,schedule,"2026-10-31")

def test_rejects_stale_schedule():
    board,schedule=fixture()
    with pytest.raises(ValueError,match="stale"):
        validate_prediction_board(board,schedule,"2026-11-10")

def test_rejects_missing_game():
    board,schedule=fixture()
    schedule.loc[len(schedule)]=dict(game_id="y",season=2026,week=8,game_type="REG",
                                    gameday="2026-11-01",home_score=None,away_score=None)
    with pytest.raises(ValueError,match="coverage mismatch"):
        validate_prediction_board(board,schedule,"2026-10-31")
