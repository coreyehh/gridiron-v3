import unittest
from scripts.phase43_projection_error_report import evaluate
def export():
    return {"source":"phase43_original_locked_snapshot","snapshot_sha256":"test-digest",
            "projections":[{"fixture_id":"g","player_id":"p","market":"receiving_yards",
                "point_projection":60.0,"forecast_at_utc":"2026-10-01T12:00:00Z","snapshot_sha256":"test-digest","line_specific_probability":None,
                "approved_wager":False},
                {"fixture_id":"g","player_id":"q","market":"receiving_yards",
                "point_projection":40.0,"forecast_at_utc":"2026-10-01T12:00:00Z","snapshot_sha256":"test-digest","line_specific_probability":None,
                "approved_wager":False}]}
def observed():
    return [{"fixture_id":"g","player_id":"p","market":"receiving_yards",
             "actual":50.0,"result_verified":True}]
class Tests(unittest.TestCase):
    def test_error_and_missing_observation(self):
        x=evaluate(export(),observed(),min_sample=1)
        self.assertEqual(x["markets"]["receiving_yards"]["mae"],10)
        self.assertEqual(x["markets"]["receiving_yards"]["mean_error"],10)
        self.assertEqual(x["unmatched_projection_count"],1)
        self.assertEqual(x["approved_wagers"],0)
    def test_unverified_result_rejected(self):
        o=observed();o[0]["result_verified"]=False
        with self.assertRaisesRegex(ValueError,"Unverified"):evaluate(export(),o)
    def test_duplicate_observation_rejected(self):
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            evaluate(export(),observed()+observed())
    def test_no_zero_imputation(self):
        x=evaluate(export(),[],min_sample=1)
        self.assertEqual(x["markets"],{})
        self.assertEqual(x["unmatched_projection_count"],2)
    def test_missing_snapshot_lock_rejected(self):
        e=export();del e["projections"][0]["snapshot_sha256"]
        with self.assertRaisesRegex(ValueError,"lock metadata"):evaluate(e,observed())
    def test_mismatched_digest_rejected(self):
        e=export();e["projections"][0]["snapshot_sha256"]="different"
        with self.assertRaisesRegex(ValueError,"digest mismatch"):evaluate(e,observed())
    def test_wager_claim_rejected(self):
        e=export();e["projections"][0]["approved_wager"]=True
        with self.assertRaisesRegex(ValueError,"wager claim"):evaluate(e,observed())
if __name__=="__main__":unittest.main()
