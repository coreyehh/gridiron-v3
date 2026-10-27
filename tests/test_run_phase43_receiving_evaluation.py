import unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from scripts.phase43_multimarket_forecasts import STAT_MAP
from scripts.run_phase43_receiving_evaluation import run

def data():
    rows=[]
    for wk in range(1,11):
        row={k:0 for k in set(STAT_MAP.values())}
        row.update(season=2026,week=wk,player_id="p1",position="WR",
                   recent_team="CIN",receptions=5,receiving_yards=65)
        rows.append(row)
    return pd.DataFrame(rows)

class Tests(unittest.TestCase):
    def test_real_runner_bounds_window_and_preserves_source_hashes(self):
        def fake_download(year,folder):
            frame=data() if year==2026 else data().iloc[:0].copy()
            return frame,{"sha256":str(year)*8,"rows":len(frame),"source":"fixture"}
        with patch("scripts.run_phase43_receiving_evaluation.download",side_effect=fake_download):
            result=run("/tmp/gridiron-receiving-evaluation-test",first_week=4,last_week=18,min_samples=3)
        self.assertEqual(result["actual_last_week"],10)
        self.assertEqual(result["source_manifest"]["2026"]["rows"],10)
        self.assertEqual(result["approved_wagers"],0)
        self.assertGreater(result["scored_records"],0)
    def test_workflow_executes_real_runner(self):
        text=Path(".github/workflows/phase43-receiving-evaluation.yml").read_text()
        self.assertIn("python -m scripts.run_phase43_receiving_evaluation",text)
        self.assertIn("actions/upload-artifact@v4",text)
if __name__=="__main__":unittest.main()
