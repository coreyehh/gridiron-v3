import unittest
from scripts.phase12 import canonical,match_player,empirical_over

class Phase12Tests(unittest.TestCase):
    def test_unicode_suffix_normalization(self):
        self.assertEqual(canonical("José Smith Jr."),canonical("Jose Smith"))
    def test_unique_current_team_season(self):
        rows=[{"player_id":"id1","player_name":"John Doe","team":"CIN","season":2026},
              {"player_id":"id2","player_name":"John Doe","team":"NYJ","season":2026}]
        r=match_player("John Doe","CIN",rows,2026)
        self.assertEqual(r["status"],"IDENTITY_MATCHED_NOT_ACTIVE_VERIFIED")
        self.assertEqual(r["player_id"],"id1")
        self.assertEqual(match_player("John Doe","CIN",rows,2025)["status"],"UNRESOLVED")
        self.assertEqual(match_player("John Doe",None,rows,2026)["status"],"UNRESOLVED")
    def test_ambiguous_ids_rejected(self):
        rows=[{"player_id":"a","player_name":"Same Name","team":"CIN","season":2026},
              {"player_id":"b","player_name":"Same Name","team":"CIN","season":2026}]
        self.assertEqual(match_player("Same Name","CIN",rows,2026)["status"],"AMBIGUOUS")
    def test_probability_diagnostic_bounded(self):
        p=empirical_over(2.0,2.5,[-2]*75+[3]*25)
        self.assertGreater(p,0);self.assertLess(p,1)
    def test_no_short_calibration_cohort(self):
        with self.assertRaises(ValueError):
            empirical_over(2.0,2.5,[0]*49)
if __name__=="__main__":unittest.main()
