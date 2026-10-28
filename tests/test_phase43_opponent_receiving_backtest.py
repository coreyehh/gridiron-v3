import unittest
import pandas as pd
from scripts.phase43_opponent_receiving_backtest import evaluate

class BacktestTests(unittest.TestCase):
    def fixture(self):
        rows=[]
        for week in range(1,9):
            for pid,opp,base in (("p1","A",70),("p2","B",35),("p3","A",50)):
                rows.append({"season":2026,"week":week,"player_id":pid,
                             "position":"WR","opponent_team":opp,
                             "receptions":5 if pid=="p1" else 3,
                             "receiving_yards":base+(week%2)*10})
        return pd.DataFrame(rows)

    def test_future_outcome_cannot_change_earlier_score(self):
        data=self.fixture()
        a=evaluate(data,first_week=6,last_week=6,shrink_games=2)
        modified=data.copy()
        modified.loc[modified.week==8,"receiving_yards"]=9999
        b=evaluate(modified,first_week=6,last_week=6,shrink_games=2)
        self.assertEqual(a,b)
        self.assertEqual(a["approved_wagers"],0)

    def test_missing_opponent_identity_fails_closed(self):
        data=self.fixture().drop(columns=["opponent_team"])
        with self.assertRaises(ValueError):
            evaluate(data)

if __name__=="__main__":
    unittest.main()
