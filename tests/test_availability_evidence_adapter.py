import unittest
from datetime import datetime,timezone
from scripts.availability_evidence_adapter import normalize
NOW=datetime(2026,10,26,23,tzinfo=timezone.utc)
def item(evidence=None):
    return {"fixtures":[{"id":"2026-W08-CIN-at-BAL","players":[{"player_id":"p1","team":"CIN","evidence":evidence}]}]}
class AdapterTests(unittest.TestCase):
    def test_unverified_evidence_fails_closed(self):
        r=normalize(item(),asof_utc=NOW)
        self.assertEqual(r["approved_wagers"],0)
        self.assertEqual(r["official_active_evidence_complete_count"],0)
        self.assertEqual(r["results"][0]["status"],"NO_BET")
    def test_duplicate_player_fixture_rejected(self):
        d=item();d["fixtures"][0]["players"].append(dict(d["fixtures"][0]["players"][0]))
        with self.assertRaisesRegex(ValueError,"Duplicate"):normalize(d,asof_utc=NOW)
    def test_malformed_fixture_rejected(self):
        with self.assertRaises(ValueError):normalize({"fixtures":[{"players":[]}]},asof_utc=NOW)
    def test_no_live_verification_claim(self):
        r=normalize({"fixtures":[]},asof_utc=NOW)
        self.assertFalse(r["source_verified_by_adapter"])
        self.assertEqual(r["approved_wagers"],0)
if __name__=="__main__":unittest.main()
