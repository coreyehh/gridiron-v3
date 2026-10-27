import unittest
from datetime import datetime,timedelta,timezone
from scripts.market_accountability_report import report
from scripts.pregame_prediction_ledger import attach_outcomes,fingerprint
START=datetime(2026,9,1,tzinfo=timezone.utc)
def row(i,market="receptions"):
    kickoff=START+timedelta(days=i)
    return {"fixture_id":str(i),"player_id":"p","market":market,
            "selection":"over","probability":.6,"model_version":"v3",
            "forecast_at_utc":(kickoff-timedelta(hours=2)).isoformat(),
            "kickoff_utc":kickoff.isoformat(),"decimal_odds":2.0,"stake_units":1}
def verified(rows):
    return attach_outcomes(rows,[{"forecast_id":fingerprint(r),"outcome":i%2,
                                  "result_verified":True} for i,r in enumerate(rows)])
class Tests(unittest.TestCase):
    def test_market_roi(self):
        x=report(verified([row(i) for i in range(10)]))["markets"]["receptions"]
        self.assertEqual(x["n"],10)
        self.assertAlmostEqual(x["hit_rate"],.5)
        self.assertAlmostEqual(x["realized_roi"],0)
        self.assertIsNotNone(x["brier_score"])
    def test_no_price_no_roi(self):
        d=verified([row(i) for i in range(10)])
        del d[0]["decimal_odds"]
        self.assertIsNone(report(d)["markets"]["receptions"]["realized_roi"])
    def test_unverified_rejected(self):
        with self.assertRaisesRegex(ValueError,"verification"):
            report([{**row(0),"outcome":1,"result_verified":False}])
    def test_small_sample_no_calibration_claim(self):
        x=report(verified([row(i) for i in range(3)]))["markets"]["receptions"]
        self.assertFalse(x["minimum_sample_met"])
        self.assertIsNone(x["brier_score"])
    def test_market_separation(self):
        d=verified([row(i) for i in range(10)]+[row(i+10,"rushing_yards") for i in range(10)])
        self.assertEqual(len(report(d)["markets"]),2)
if __name__=="__main__":unittest.main()
