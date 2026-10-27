import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from scripts.reconcile_phase43_observed_boxes import reconcile
from scripts.phase43_multimarket_forecasts import VERSION
from scripts.phase31_accountability import digest
class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name)
        self.schedule=root/"schedule.csv"
        self.schedule.write_text("season,week,game_type,home_team,away_team,home_score,away_score\n2026,7,REG,CIN,BAL,24,17\n")
        self.schedule_hash=hashlib.sha256(self.schedule.read_bytes()).hexdigest()
        self.stats=root/"stats.parquet";self.stats.write_bytes(b"pinned stats fixture")
        self.stats_hash=hashlib.sha256(self.stats.read_bytes()).hexdigest()
        self.patcher=patch("scripts.nflverse_result_verifier.pd.read_parquet",return_value=pd.DataFrame(
            [{"season":2026,"week":7,"player_id":"p1","receiving_yards":80}]))
        self.patcher.start();self.addCleanup(self.patcher.stop)
        x={"version":VERSION,"created_at_utc":"2026-10-01T12:00:00Z",
           "fixtures":[{"id":"2026-W07-BAL-at-CIN","gameday":"2026-10-20"}],
           "forecasts":[{"fixture_id":"2026-W07-BAL-at-CIN","player_id":"p1","team":"CIN",
                         "point_projections":{"receiving_yards":70}},
                        {"fixture_id":"2026-W07-BAL-at-CIN","player_id":"missing","team":"CIN",
                         "point_projections":{"receiving_yards":40}}],
           "past_fixture_forecasts_reconstructed":False}
        x["payload_sha256"]=digest(x)
        self.snapshot=x
    def run_audit(self):
        return reconcile(self.snapshot,schedule_path=self.schedule,
           schedule_sha256=self.schedule_hash,stats_path=self.stats,
           stats_sha256=self.stats_hash,min_sample=1)
    def test_real_source_match_and_missing_player(self):
        x=self.run_audit()
        self.assertEqual(x["matched_observations"],1)
        self.assertEqual(x["markets"]["receiving_yards"]["mae"],10)
        self.assertEqual(x["unmatched_projection_count"],1)
        self.assertFalse(x["external_source_authenticity_certified"])
    def test_wrong_stats_hash_rejected(self):
        with self.assertRaisesRegex(ValueError,"hash mismatch"):
            reconcile(self.snapshot,schedule_path=self.schedule,
                schedule_sha256=self.schedule_hash,stats_path=self.stats,
                stats_sha256="fake")
    def test_snapshot_tampering_rejected(self):
        self.snapshot["forecasts"][0]["point_projections"]["receiving_yards"]=999
        with self.assertRaisesRegex(ValueError,"digest"):self.run_audit()
if __name__=="__main__":unittest.main()
