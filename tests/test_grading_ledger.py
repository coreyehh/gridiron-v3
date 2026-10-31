import pandas as pd
import pytest
from matchup_engine.ledger import append_grading_ledger,verify_grading_ledger

def test_append_and_verify(tmp_path):
    grade=pd.DataFrame([dict(game_id="g",winner_correct=1)])
    sha="a"*64
    entry=append_grading_ledger(grade,{"graded_games":1},tmp_path,sha)
    assert verify_grading_ledger(tmp_path)=={"entries":1,"verified":True}
    with pytest.raises(ValueError,match="already recorded"):
        append_grading_ledger(grade,{"graded_games":1},tmp_path,sha)
    (tmp_path/entry["grades_file"]).write_text("tampered")
    with pytest.raises(ValueError,match="integrity"):
        verify_grading_ledger(tmp_path)
