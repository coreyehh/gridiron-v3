"""Regression checks that the Phase43 runner reports eligibility without approving bets."""
import unittest
from pathlib import Path

class Tests(unittest.TestCase):
    def test_runner_calls_eligibility_on_both_lock_paths(self):
        src=Path("scripts/phase43_multimarket_forecasts.py").read_text()
        self.assertIn("evidence=eligibility_audit(existing)",src)
        self.assertIn("evidence=eligibility_audit(snap)",src)
        self.assertIn('result["verified_active_count"]',src)
        self.assertIn('"sportsbook_requests":0,"qualified_bets":0',src)
if __name__=="__main__":unittest.main()
