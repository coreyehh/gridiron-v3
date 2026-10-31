import pandas as pd
import pytest
from matchup_engine.upcoming import upcoming_board

def test_upcoming_requires_unplayed_games():
    frame=pd.DataFrame([dict(game_id="g1",season=2025,week=1,
        gameday="2025-09-01",home_team="A",away_team="B",game_type="REG",
        home_score=7,away_score=3)])
    with pytest.raises(ValueError,match="No unplayed"):
        upcoming_board(frame,"2025-09-02")

def test_missing_schedule_fields_rejected():
    with pytest.raises(ValueError,match="Missing schedule"):
        upcoming_board(pd.DataFrame(),"2025-09-01")
