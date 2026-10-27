import unittest
from scripts.phase43_snapshot_quality_audit import audit
from scripts.phase43_multimarket_forecasts import VERSION
from scripts.phase31_accountability import digest
def snap():
    x={"version":VERSION,"created_at_utc":"2026-10-18T12:00:00Z",
       "fixtures":[{"id":"2026-W06-WAS-at-SF","home":"SF","away":"WAS","gameday":"2026-10-19"}],
       "forecasts":[{"fixture_id":"2026-W06-WAS-at-SF","player_id":"p1",
           "player_name":"Test Player","team":"WAS","active_verified":False,
           "role_verified":False,"last_observed_season":2026,
           "last_observed_week":4,"point_projections":{"rushing_yards":12.0}}],
       "past_fixture_forecasts_reconstructed":False}
    x["payload_sha256"]=digest(x)
    return x
class Tests(unittest.TestCase):
    def test_unverified_roles_visible(self):
        x=audit(snap())
        self.assertEqual(x["forecast_players"],1)
        self.assertEqual(x["issue_counts"]["ACTIVE_STATUS_UNVERIFIED"],1)
        self.assertEqual(x["issue_counts"]["ROLE_UNVERIFIED"],1)
        self.assertFalse(x["ready_for_wager_approval"])
    def test_wrong_team_flagged(self):
        x=snap();x["forecasts"][0]["team"]="DAL"
        x["payload_sha256"]=digest({k:v for k,v in x.items() if k!="payload_sha256"})
        self.assertEqual(audit(x)["issue_counts"]["TEAM_OUTSIDE_FIXTURE"],1)
    def test_tampered_lock_rejected(self):
        x=snap();x["forecasts"][0]["team"]="DAL"
        with self.assertRaisesRegex(ValueError,"digest"):audit(x)
if __name__=="__main__":unittest.main()
