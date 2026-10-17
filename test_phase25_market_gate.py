import unittest
from scripts.phase25_market_gate import (decimal_price,price_ev,joint_book_pair,
  validate_offer,eligibility,analyze_quotes,markdown)
NOW="2026-10-16T21:00:00Z"
def quote(side,odds,**changes):
    row={"event_id":"event1","season":2026,"home_team":"LA","away_team":"SF",
     "kickoff_utc":"2026-10-17T00:00:00Z","player_display_name":"Example Player",
     "market":"receptions","side":side,"line":3.5,
     "american_odds":odds,"bookmaker":"testbook",
     "quoted_at_utc":"2026-10-16T20:45:00Z",
     "captured_at_utc":"2026-10-16T21:00:00Z",
     "player_id_verified":False}
    row.update(changes);return row
class Market25Tests(unittest.TestCase):
    def test_price_math(self):
        self.assertAlmostEqual(decimal_price(-110),1.909090909,places=5)
        self.assertAlmostEqual(price_ev(.60,-110),.145454545,places=5)
        self.assertLess(price_ev(.50,-110),0)
    def test_two_sided_vig(self):
        result=joint_book_pair(quote("over",-110),quote("under",-110))
        self.assertAlmostEqual(result["over_no_vig"],.5)
        self.assertGreater(result["hold"],0)
        self.assertAlmostEqual(result["over_break_even"],.5238095,places=5)
    def test_mismatched_line_or_book_rejected(self):
        with self.assertRaises(ValueError):
            joint_book_pair(quote("over",-110),quote("under",-110,line=4.5))
        with self.assertRaises(ValueError):
            joint_book_pair(quote("over",-110),quote("under",-110,bookmaker="another"))
    def test_timestamps_and_stale_quote(self):
        with self.assertRaises(ValueError):
            validate_offer(quote("over",-110,captured_at_utc="2026-10-17T00:01:00Z"),"2026-10-17T00:01:00Z")
        with self.assertRaises(ValueError):
            validate_offer(quote("over",-110,quoted_at_utc="2026-10-16T15:00:00Z"),NOW)
    def test_missing_verified_inputs_cannot_qualify(self):
        row=quote("over",-110)
        gate=eligibility(row,probability=None,has_price_pair=True)
        self.assertFalse(gate["eligible"])
        self.assertIn("unverified_active",gate["reasons"])
        self.assertIn("no_real_line_probability_calibration",gate["reasons"])
    def test_aggregate_contains_no_player_or_provider_lines(self):
        report=analyze_quotes([quote("over",-110),quote("under",-110)],NOW)
        self.assertEqual(report["counts"]["valid_two_sided_pairs"],1)
        self.assertEqual(report["qualified_bets"],0)
        payload=str(report)+markdown(report)
        self.assertNotIn("Example Player",payload)
        self.assertNotIn("testbook",payload)
        self.assertNotIn("3.5",payload)
    def test_duplicate_side_not_pair(self):
        report=analyze_quotes([quote("over",-110),quote("over",-115)],NOW)
        self.assertEqual(report["counts"].get("valid_two_sided_pairs",0),0)
    def test_bad_probabilities_rejected(self):
        for prob in (-.1,1.1,float("nan")):
            with self.assertRaises(ValueError):
                price_ev(prob,-110)
if __name__=="__main__":unittest.main()
