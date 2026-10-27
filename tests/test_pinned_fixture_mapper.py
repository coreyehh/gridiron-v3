import hashlib,tempfile,unittest
from pathlib import Path
from scripts.pinned_fixture_mapper import fixture_weeks
ROWS="season,week,game_type,home_team,away_team,home_score,away_score\n2026,7,REG,CIN,BAL,24,17\n2026,8,REG,CIN,PIT,,\n2026,7,POST,CIN,BUF,21,14\n"
class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"schedule.csv";self.path.write_text(ROWS)
        self.sha=hashlib.sha256(self.path.read_bytes()).hexdigest()
    def test_completed_only(self):
        x=fixture_weeks(self.path,expected_sha256=self.sha)
        self.assertEqual(x,{"2026-W07-BAL-at-CIN":(2026,7)})
    def test_wrong_hash_rejected(self):
        with self.assertRaisesRegex(ValueError,"hash mismatch"):
            fixture_weeks(self.path,expected_sha256="wrong")
    def test_duplicate_completed_fixture_rejected(self):
        self.path.write_text(ROWS+"2026,7,REG,CIN,BAL,24,17\n")
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            fixture_weeks(self.path,expected_sha256=hashlib.sha256(self.path.read_bytes()).hexdigest())
if __name__=="__main__":unittest.main()
