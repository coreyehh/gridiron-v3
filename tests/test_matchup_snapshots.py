import hashlib
import json
import pandas as pd
import pytest
from matchup_engine.snapshots import save_prediction_snapshot

def test_snapshot_is_hashable_and_non_overwriting(tmp_path):
    frame=pd.DataFrame([dict(game_id="x",home_win_probability=.6)])
    stamp="2026-10-31T15:00:00Z"
    csv,metadata=save_prediction_snapshot(frame,tmp_path,"2026-10-31",stamp)
    assert hashlib.sha256(csv.read_bytes()).hexdigest()==json.loads(metadata.read_text())["sha256"]
    with pytest.raises(FileExistsError):
        save_prediction_snapshot(frame,tmp_path,"2026-10-31",stamp)

def test_snapshot_rejects_empty(tmp_path):
    with pytest.raises(ValueError,match="empty"):
        save_prediction_snapshot(pd.DataFrame(),tmp_path,"2026-10-31")
