import unittest
import pandas as pd
from scripts.phase43_opponent_receiving_context import opponent_context

class OpponentContextTests(unittest.TestCase):
    def test_future_rows_cannot_change_pregame_context(self):
        data=pd.DataFrame([
            {"season":2026,"week":1,"position":"WR","opponent_team":"A","receiving_yards":80},
            {"season":2026,"week":2,"position":"WR","opponent_team":"B","receiving_yards":40},
            {"season":2026,"week":3,"position":"WR","opponent_team":"A","receiving_yards":100},
            {"season":2026,"week":5,"position":"WR","opponent_team":"A","receiving_yards":9999},
        ])
        a=opponent_context(data,opponent="A",position="WR",season=2026,week=4)
        b=opponent_context(data.iloc[:3],opponent="A",position="WR",season=2026,week=4)
        self.assertEqual(a,b)
        self.assertEqual(a["sample_size"],2)
        self.assertGreater(a["shrunk_multiplier"],1)
        self.assertLess(a["shrunk_multiplier"],1.5)
        self.assertEqual(a["approved_wagers"],0)

    def test_missing_opponent_identity_fails_closed(self):
        data=pd.DataFrame({"season":[2026],"week":[1],"position":["WR"],"receiving_yards":[30]})
        with self.assertRaises(ValueError):
            opponent_context(data,opponent="A",position="WR",season=2026,week=2)

    def test_unknown_opponent_does_not_invent_strength(self):
        data=pd.DataFrame([{"season":2026,"week":1,"position":"TE",
                            "opponent_team":"A","receptions":3}])
        out=opponent_context(data,opponent="B",position="TE",season=2026,week=2,market="receptions")
        self.assertIsNone(out["shrunk_multiplier"])

if __name__=="__main__":
    unittest.main()
