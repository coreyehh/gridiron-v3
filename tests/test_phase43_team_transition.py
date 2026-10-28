import unittest
from pathlib import Path
from scripts.phase43_snapshot_quality_audit import audit
from scripts.phase43_multimarket_forecasts import VERSION
from scripts.phase31_accountability import digest

class Tests(unittest.TestCase):
    def test_player_history_not_filtered_to_current_team(self):
        source=Path("scripts/phase43_multimarket_forecasts.py").read_text()
        self.assertIn('observed=prior[prior.player_id.astype(str)==pid]',source)
        self.assertIn('info["historical_team_transition"]=last_team!=club',source)
    def test_transition_disclosed_in_quality_audit(self):
        snap={"version":VERSION,"created_at_utc":"2026-10-18T12:00:00Z",
          "fixtures":[{"id":"2026-W06-WAS-at-SF","home":"SF","away":"WAS","gameday":"2026-10-19"}],
          "forecasts":[{"fixture_id":"2026-W06-WAS-at-SF","player_id":"p1",
            "player_name":"Example","team":"WAS","last_observed_team":"TEN",
            "historical_team_transition":True,"last_observed_season":2026,
            "last_observed_week":5,"active_verified":False,"role_verified":False,
            "point_projections":{"receiving_yards":22.0}}],
          "past_fixture_forecasts_reconstructed":False}
        snap["payload_sha256"]=digest(snap)
        self.assertEqual(audit(snap)["issue_counts"]["HISTORICAL_TEAM_TRANSITION"],1)
if __name__=="__main__":unittest.main()
