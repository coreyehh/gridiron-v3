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

    def test_opponent_strength_adjustment_uses_prior_player_expectations(self):
        rows=[]
        for week in range(1,9):
            rows.append({"season":2026,"week":week,"player_id":"p1",
                         "position":"WR","opponent_team":"A" if week>=4 else "B",
                         "receiving_yards":80 if week>=4 else 40})
        data=pd.DataFrame(rows)
        out=opponent_context(data,opponent="A",position="WR",season=2026,week=8,
                             shrink_games=3)
        self.assertGreaterEqual(out["opponent_strength_adjusted_samples"],3)
        self.assertIsNotNone(out["opponent_strength_adjusted_multiplier"])
        future=data.copy()
        future.loc[future.week==8,"receiving_yards"]=9999
        self.assertEqual(out,opponent_context(future,opponent="A",position="WR",
                         season=2026,week=8,shrink_games=3))

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
