import json,tempfile,unittest
from pathlib import Path
from scripts.pregame_prediction_ledger import append,attach_outcomes,fingerprint
from scripts.probability_calibration_audit import evaluate
def row(i):
    return {"fixture_id":str(i),"player_id":"p","market":"receptions",
            "selection":"over","probability":.6,
            "forecast_at_utc":"2026-10-01T17:00:00Z",
            "kickoff_utc":"2026-10-01T20:00:00Z",
            "model_version":"v3-test"}
class Tests(unittest.TestCase):
    def test_append_and_immutability(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"ledger.jsonl"
            entry=append(path,row(0))
            self.assertEqual(entry["forecast_id"],fingerprint(row(0)))
            with self.assertRaisesRegex(ValueError,"Duplicate"):append(path,row(0))
            self.assertEqual(len(path.read_text().splitlines()),1)
    def test_reject_post_kickoff(self):
        r=row(0);r["forecast_at_utc"]=r["kickoff_utc"]
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"precede kickoff"):append(Path(d)/"l",r)
    def test_reject_outcome_in_pregame(self):
        r=row(0);r["outcome"]=1
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"Outcome"):append(Path(d)/"l",r)
    def test_verified_outcomes_join_for_audit(self):
        forecasts=[row(i) for i in range(10)]
        results=[{"forecast_id":fingerprint(r),"outcome":i%2,"result_verified":True}
                 for i,r in enumerate(forecasts)]
        joined=attach_outcomes(forecasts,results)
        self.assertEqual(evaluate(joined)["n"],10)
        self.assertNotIn("outcome",forecasts[0])
    def test_unverified_result_rejected(self):
        with self.assertRaisesRegex(ValueError,"Unverified"):
            attach_outcomes([row(0)],[{"forecast_id":fingerprint(row(0)),"outcome":1,"result_verified":False}])
if __name__=="__main__":unittest.main()
