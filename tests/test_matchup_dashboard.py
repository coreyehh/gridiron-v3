import pandas as pd
import pytest
from matchup_engine.dashboard import render_matchup_dashboard,write_matchup_dashboard

def board():
    return pd.DataFrame([dict(game_id="g",gameday="2026-11-01",home_team="CIN",
      away_team="PIT",projected_winner="CIN",home_win_probability=.65,
      fair_home_spread=-4.5,pred_total=46.,projected_home_points=25.25,
      projected_away_points=20.75,model_status="PRELIMINARY_BASELINE_NO_INJURY_OR_MARKET_ADJUSTMENT")])

def test_dashboard_discloses_model_limitations(tmp_path):
    html=render_matchup_dashboard(board(),{"graded_games":0,"winner_accuracy":None})
    assert "NOT OFFICIAL WAGERS" in html
    assert "65.0%" in html
    assert "-4.5" in html
    assert "Pending" in html
    assert write_matchup_dashboard(board(),tmp_path/"dashboard.html").exists()

def test_dashboard_rejects_duplicate_game():
    data=pd.concat([board(),board()],ignore_index=True)
    with pytest.raises(ValueError,match="Duplicate"):
        render_matchup_dashboard(data)

def test_dashboard_escapes_untrusted_text():
    data=board()
    data.loc[0,"away_team"]="<script>alert(1)</script>"
    assert "&lt;script&gt;" in render_matchup_dashboard(data)
