import unittest
import pandas as pd
from scripts.phase43_multimarket_forecasts import STAT_MAP,prep,forecast_player

class Tests(unittest.TestCase):
    def test_receiving_markets_available(self):
        self.assertEqual(STAT_MAP["receptions"],"receptions")
        self.assertEqual(STAT_MAP["receiving_yards"],"receiving_yards")
    def test_receiving_forecasts_from_observed_games(self):
        rows=[]
        for week in range(1,6):
            row={k:0 for k in set(STAT_MAP.values())}
            row.update(season=2026,week=week,player_id="p1",position="WR",
                       recent_team="CIN",receptions=5,receiving_yards=65)
            rows.append(row)
        result=forecast_player(prep(pd.DataFrame(rows)),"WR")
        self.assertEqual(result["point_projections"]["receptions"],5)
        self.assertEqual(result["point_projections"]["receiving_yards"],65)
        self.assertFalse(result["eligible_for_wager_approval"])
    def test_missing_receiving_column_rejected(self):
        row={k:0 for k in set(STAT_MAP.values())}
        row.update(season=2026,week=1,player_id="p1",position="WR",recent_team="CIN")
        del row["receptions"]
        with self.assertRaisesRegex(ValueError,"receptions"):
            prep(pd.DataFrame([row]))
if __name__=="__main__":unittest.main()
