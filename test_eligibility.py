"""Deterministic tests for selection and chronological split."""
import unittest
import pandas as pd
from scripts.evaluate_eligible import evaluate, prepare

class EligibilityTests(unittest.TestCase):
    def test_requires_lagged_features(self):
        with self.assertRaises(ValueError):
            prepare(pd.DataFrame({"season":[2025]}))
    def test_pregame_pool_does_not_use_current_result_as_threshold(self):
        columns = ["prior5_receptions","prior5_receiving_yards","prior5_rushing_yards","prior5_passing_yards",
                   "prior3_receptions","prior3_receiving_yards","prior3_rushing_yards","prior3_passing_yards"]
        rows=[]
        for year in [2021,2022,2023,2024,2025]:
            for i in range(12):
                a={"season":year,"week":i+1,"player_id":"WR1","prior_position":"WR","prior_observations":i+3,
                   "receptions":1,"receiving_yards":0 if i%2 else 100,
                   "rushing_yards":0,"passing_yards":0}
                for col in columns: a[col]=30 if "receiving_yards" in col else (2 if "receptions" in col else 0)
                rows.append(a)
        result=evaluate(pd.DataFrame(rows))
        wr=next(x for x in result["results"] if x["position"]=="WR" and x["market"]=="receiving_yards")
        self.assertEqual(wr["test_n"],12)
        self.assertEqual(wr["status"],"insufficient_samples")
        self.assertFalse(result["roi_calculated"])

if __name__=="__main__":
    unittest.main()
