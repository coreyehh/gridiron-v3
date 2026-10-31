import json
import pandas as pd
import pytest
from matchup_engine.snapshots import save_prediction_snapshot
from matchup_engine.grade_snapshots import grade_prediction_snapshot

def sample(tmp_path):
    board=pd.DataFrame([dict(game_id="g",gameday="2026-11-01",
        home_team="CIN",away_team="PIT",home_win_probability=.7,
        projected_home_points=27.,projected_away_points=20.,
        fair_home_spread=-7.,pred_total=47.)])
    csv,meta=save_prediction_snapshot(board,tmp_path,"2026-10-31",
                                      "2026-10-31T12:00:00Z")
    results=pd.DataFrame([dict(game_id="g",gameday="2026-11-01",
        home_team="CIN",away_team="PIT",home_score=24.,away_score=17.)])
    return csv,meta,results

def test_grades_winner_and_errors(tmp_path):
    csv,meta,results=sample(tmp_path)
    graded,m=grade_prediction_snapshot(csv,meta,results)
    assert m["graded_games"]==1
    assert m["winner_accuracy"]==1
    assert m["margin_mae"]==0
    assert m["total_mae"]==6
    assert abs(m["brier"]-.09)<1e-9

def test_unplayed_game_is_pending(tmp_path):
    csv,meta,results=sample(tmp_path)
    results.loc[0,["home_score","away_score"]]=[float("nan"),float("nan")]
    _,m=grade_prediction_snapshot(csv,meta,results)
    assert m["pending_games"]==1
    assert m["winner_accuracy"] is None

def test_tampered_snapshot_is_rejected(tmp_path):
    csv,meta,results=sample(tmp_path)
    csv.write_text(csv.read_text()+"\n")
    with pytest.raises(ValueError,match="integrity"):
        grade_prediction_snapshot(csv,meta,results)

def test_rejects_same_day_snapshot(tmp_path):
    csv,meta,results=sample(tmp_path)
    details=json.loads(meta.read_text())
    details["generated_at_utc"]="2026-11-01T12:00:00+00:00"
    meta.write_text(json.dumps(details))
    with pytest.raises(ValueError,match="not provably pregame"):
        grade_prediction_snapshot(csv,meta,results)

def test_tie_does_not_count_as_wrong_winner(tmp_path):
    csv,meta,results=sample(tmp_path)
    results.loc[0,["home_score","away_score"]]=[20.,20.]
    _,metrics=grade_prediction_snapshot(csv,meta,results)
    assert metrics["winner_accuracy"] is None or pd.isna(metrics["winner_accuracy"])
    assert metrics["margin_mae"]==7.
