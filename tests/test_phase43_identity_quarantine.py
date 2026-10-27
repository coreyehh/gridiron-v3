import unittest
import pandas as pd
from scripts.phase43_multimarket_forecasts import prep,REQUIRED
def frame(ids):
    rows=[]
    for i,pid in enumerate(ids):
        d={k:0 for k in REQUIRED}
        d.update(season=2026,week=1,player_id=pid,position="WR",
                 team="CIN",receptions=2,receiving_yards=20)
        rows.append(d)
    return pd.DataFrame(rows)
class Tests(unittest.TestCase):
    def test_null_and_blank_ids_quarantined(self):
        x=prep(frame(["p1",None,""]))
        self.assertEqual(x["player_id"].tolist(),["p1"])
    def test_all_missing_ids_rejected(self):
        with self.assertRaisesRegex(ValueError,"No identified"):prep(frame([None,""]))
    def test_identified_duplicate_rejected(self):
        with self.assertRaisesRegex(ValueError,"Duplicate"):prep(frame(["p1","p1"]))
if __name__=="__main__":unittest.main()
