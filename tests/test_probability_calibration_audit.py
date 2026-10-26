import unittest
from datetime import datetime,timedelta,timezone
from scripts.probability_calibration_audit import evaluate,chronological_split
START=datetime(2026,9,1,tzinfo=timezone.utc)
def row(i,p=.6,y=1):
    k=START+timedelta(days=i)
    return {"fixture_id":str(i),"player_id":"p","market":"receiving_yards",
            "selection":"over","probability":p,"outcome":y,
            "forecast_at_utc":(k-timedelta(hours=2)).isoformat(),
            "kickoff_utc":k.isoformat()}
class Tests(unittest.TestCase):
    def test_perfect_forecasts(self):
        r=evaluate([row(i,float(i%2),i%2) for i in range(10)])
        self.assertEqual(r["brier_score"],0)
        self.assertFalse(r["live_probability_calibrated"])
    def test_miscalibration_detected(self):
        r=evaluate([row(i,.9,0) for i in range(10)])
        self.assertGreater(r["brier_score"],.8)
    def test_post_kickoff_leakage_rejected(self):
        d=[row(i) for i in range(10)]
        d[0]["forecast_at_utc"]=d[0]["kickoff_utc"]
        with self.assertRaisesRegex(ValueError,"Post-kickoff"):evaluate(d)
    def test_duplicate_forecast_rejected(self):
        d=[row(i) for i in range(10)]
        d.append(dict(d[0]))
        with self.assertRaisesRegex(ValueError,"Duplicate"):evaluate(d)
    def test_chronological_split(self):
        train,test=chronological_split([row(i) for i in range(12)])
        self.assertLess(max(x["kickoff_utc"] for x in train),min(x["kickoff_utc"] for x in test))
    def test_same_kickoff_cohort_not_split(self):
        d=[row(i) for i in range(12)]
        d[8]["kickoff_utc"]=d[9]["kickoff_utc"]
        train,test=chronological_split(d)
        self.assertTrue(set(x["kickoff_utc"] for x in train).isdisjoint(x["kickoff_utc"] for x in test))
    def test_insufficient_data(self):
        with self.assertRaisesRegex(ValueError,"Insufficient"):evaluate([row(0)])
if __name__=="__main__":unittest.main()
