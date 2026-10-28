import unittest
import pandas as pd
from scripts.phase43_multimarket_forecasts import STAT_MAP
from scripts.phase43_receiving_threshold_walkforward import evaluate

def fixture():
    rows=[]
    for wk in range(1,11):
        row={k:0 for k in set(STAT_MAP.values())}
        row.update(season=2026,week=wk,player_id="p1",position="WR",
                   recent_team="CIN",receptions=5 if wk%2 else 3,
                   receiving_yards=80 if wk%2 else 30)
        rows.append(row)
    return pd.DataFrame(rows)

class Tests(unittest.TestCase):
    def test_chronological_brier(self):
        result=evaluate(fixture(),first_week=5,last_week=8,min_samples=3,
                thresholds={"receptions":(5,),"receiving_yards":(70,)})
        self.assertEqual(result["scored_records"],8)
        self.assertGreaterEqual(result["metrics"]["receptions:5"]["brier_score"],0)
        self.assertIsNotNone(result["metrics"]["receptions:5"]["baseline_brier_score"])
        self.assertIsNotNone(result["metrics"]["receptions:5"]["paired_brier_improvement"])
        self.assertEqual(result["promotion_decision"],"NOT_ELIGIBLE_FOR_BETTING_USE")
        self.assertFalse(result["calibrated"])
        self.assertEqual(result["approved_wagers"],0)
    def test_no_future_data(self):
        base=fixture()
        altered=base.copy()
        altered.loc[altered.week==10,"receptions"]=100
        a=evaluate(base,first_week=5,last_week=8,min_samples=3,
                   thresholds={"receptions":(5,)})
        b=evaluate(altered,first_week=5,last_week=8,min_samples=3,
                   thresholds={"receptions":(5,)})
        self.assertEqual(a["metrics"],b["metrics"])
    def test_non_receiving_positions_excluded(self):
        raw=fixture()
        qb=raw.copy()
        qb["player_id"]="qb1"
        qb["position"]="QB"
        combined=pd.concat([raw,qb],ignore_index=True)
        a=evaluate(raw,first_week=5,last_week=8,min_samples=3,
                   thresholds={"receptions":(5,)})
        b=evaluate(combined,first_week=5,last_week=8,min_samples=3,
                   thresholds={"receptions":(5,)})
        self.assertEqual(a["metrics"],b["metrics"])
        self.assertEqual(b["eligible_positions"],["WR","TE","RB"])
    def test_volume_gate_uses_only_prior_games(self):
        raw=fixture()
        a=evaluate(raw,first_week=5,last_week=8,min_samples=3,
            thresholds={"receptions":(5,)},min_prior_receptions=4)
        altered=raw.copy()
        altered.loc[altered.week==10,"receptions"]=1000
        b=evaluate(altered,first_week=5,last_week=8,min_samples=3,
            thresholds={"receptions":(5,)},min_prior_receptions=4)
        self.assertEqual(a["metrics"],b["metrics"])
        self.assertEqual(a["min_prior_receptions"],4)
        self.assertEqual(a["baseline_cohort"],"SAME_POSITION_AND_PRIOR_VOLUME")
        self.assertIn("paired_improvement_ci95",a["metrics"]["receptions:5"])
        self.assertIn("paired_n",a["metrics"]["receptions:5"])
    def test_invalid_window(self):
        with self.assertRaises(ValueError):
            evaluate(fixture(),first_week=8,last_week=4)
if __name__=="__main__":unittest.main()
