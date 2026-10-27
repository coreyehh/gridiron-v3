import hashlib,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from scripts.nflverse_result_verifier import PinnedNflverseResultVerifier
class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"stats.parquet"
        self.path.write_bytes(b"pinned test bytes")
        self.sha=hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.frame=pd.DataFrame([{"season":2026,"week":7,"player_id":"p1",
                                  "receptions":5,"receiving_yards":72}])
        self.patch=patch("scripts.nflverse_result_verifier.pd.read_parquet",return_value=self.frame)
        self.patch.start()
        self.addCleanup(self.patch.stop)
    def verifier(self):
        return PinnedNflverseResultVerifier(self.path,expected_sha256=self.sha,
                                            fixture_weeks={"game-7":(2026,7)})
    def observation(self):
        return {"fixture_id":"game-7","player_id":"p1","market":"receptions",
                "actual":5,"source_name":"nflverse_player_week",
                "source_record_id":"2026-7-p1","source_sha256":self.sha}
    def test_pinned_stat_matches(self):
        self.assertTrue(self.verifier().verify(self.observation()))
    def test_wrong_stat_rejected(self):
        self.assertFalse(self.verifier().verify({**self.observation(),"actual":6}))
    def test_wrong_fixture_rejected(self):
        self.assertFalse(self.verifier().verify({**self.observation(),"fixture_id":"unknown"}))
    def test_wrong_source_hash_rejected(self):
        self.assertFalse(self.verifier().verify({**self.observation(),"source_sha256":"fake"}))
    def test_unpinned_artifact_rejected(self):
        with self.assertRaisesRegex(ValueError,"hash mismatch"):
            PinnedNflverseResultVerifier(self.path,expected_sha256="fake",
                                          fixture_weeks={"game-7":(2026,7)})
if __name__=="__main__":unittest.main()
