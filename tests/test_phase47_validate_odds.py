import unittest
from scripts.phase47_validate_odds import validate

BASE = dict(player_id="player-123", season="2026", week="7", market="rushing_attempts",
            direction="over", line="14.5", american_odds="-110",
            quoted_at_utc="2026-10-22T18:00:00-04:00",
            kickoff_utc="2026-10-22T20:15:00-04:00", sportsbook="example")

class TestPhase47(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate(BASE)["american_odds"], -110)
    def test_positive_odds(self):
        self.assertEqual(validate(dict(BASE, american_odds="+150"))["american_odds"], 150)
    def test_missing_price(self):
        with self.assertRaises(ValueError):
            validate(dict(BASE, american_odds=""))
    def test_after_kickoff(self):
        with self.assertRaises(ValueError):
            validate(dict(BASE, quoted_at_utc="2026-10-23T01:00:00Z"))
    def test_stale(self):
        with self.assertRaises(ValueError):
            validate(dict(BASE, quoted_at_utc="2026-10-20T18:00:00-04:00"))
    def test_naive_timestamp(self):
        with self.assertRaises(ValueError):
            validate(dict(BASE, quoted_at_utc="2026-10-22T18:00:00"))
    def test_unsupported_market(self):
        with self.assertRaises(ValueError):
            validate(dict(BASE, market="mystery"))
if __name__ == "__main__":
    unittest.main()
