import unittest
from scripts.phase43_projection_ledger_export import export
from scripts.phase43_multimarket_forecasts import VERSION
from scripts.phase31_accountability import digest
def snapshot():
    x={"version":VERSION,"created_at_utc":"2026-10-26T15:00:00+00:00",
       "past_fixture_forecasts_reconstructed":False,
       "fixtures":[{"id":"g1","gameday":"2026-10-27"}],
       "forecasts":[{"fixture_id":"g1","player_id":"p1","team":"CIN",
                     "point_projections":{"receiving_yards":65.2,"anytime_touchdown":.4}}]}
    x["payload_sha256"]=digest(x)
    return x
class Tests(unittest.TestCase):
    def test_exports_points_without_probability_claim(self):
        r=export(snapshot())
        self.assertEqual(r["projection_count"],2)
        self.assertFalse(r["probability_calibrated"])
        self.assertTrue(all(z["line_specific_probability"] is None for z in r["projections"]))
        self.assertEqual(r["approved_wagers"],0)
    def test_modified_snapshot_rejected(self):
        s=snapshot();s["forecasts"][0]["point_projections"]["receiving_yards"]=100
        with self.assertRaisesRegex(ValueError,"digest"):export(s)
    def test_past_fixture_rejected(self):
        s=snapshot();s["fixtures"][0]["gameday"]="2026-10-25"
        s["payload_sha256"]=digest({k:v for k,v in s.items() if k!="payload_sha256"})
        with self.assertRaises(ValueError):export(s)
    def test_historical_reconstruction_rejected(self):
        s=snapshot();s["past_fixture_forecasts_reconstructed"]=True
        s["payload_sha256"]=digest({k:v for k,v in s.items() if k!="payload_sha256"})
        with self.assertRaisesRegex(ValueError,"reconstruction"):export(s)
if __name__=="__main__":unittest.main()
