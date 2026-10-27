import unittest
import pandas as pd
from scripts.phase43_multimarket_forecasts import STAT_MAP
from scripts.phase43_receiving_threshold_research import historical_thresholds

def boxes():
    rows=[]
    for week in range(1,11):
        row={k:0 for k in set(STAT_MAP.values())}
        row.update(season=2026,week=week,player_id="p1",position="WR",
                   recent_team="CIN",receptions=5 if week%2 else 3,
                   receiving_yards=80 if week%2 else 30)
        rows.append(row)
    return pd.DataFrame(rows)

class Tests(unittest.TestCase):
    def test_future_weeks_not_leaked(self):
        r=historical_thresholds(boxes(),"p1",season=2026,week=6,
              thresholds={"receptions":(5,),"receiving_yards":(70,)})
        self.assertEqual(r["markets"]["receptions"]["thresholds"]["5"]["observed_games"],5)
        self.assertEqual(r["markets"]["receptions"]["thresholds"]["5"]["observed_hits"],3)
        self.assertFalse(r["calibrated"])
        self.assertEqual(r["approved_wagers"],0)
    def test_no_sample(self):
        r=historical_thresholds(boxes(),"missing",season=2026,week=6)
        self.assertIsNone(r["markets"]["receptions"]["thresholds"]["5"]["empirical_hit_rate"])
    def test_invalid_observation_is_quarantined(self):
        raw=boxes()
        raw.loc[raw.week==2,"receiving_yards"]=-4
        r=historical_thresholds(raw,"p1",season=2026,week=6,
              thresholds={"receiving_yards":(70,)},min_samples=3)
        market=r["markets"]["receiving_yards"]
        self.assertEqual(market["invalid_historical_rows_quarantined"],1)
        self.assertEqual(market["sample_size"],4)
        self.assertEqual(market["thresholds"]["70"]["observed_games"],4)
    def test_invalid_threshold(self):
        with self.assertRaises(ValueError):
            historical_thresholds(boxes(),"p1",season=2026,week=6,
                                  thresholds={"receptions":(-1,)})
if __name__=="__main__":unittest.main()
