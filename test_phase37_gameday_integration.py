import unittest
from unittest.mock import patch
from scripts.phase37_gameday_integration import (
 offline_decisions,match_live_fanduel,safe_html,live_once)
from test_phase32_market_matching import snapshot,CAPTURE,KICKOFF

def data(book="fanduel",player="Drake London"):
    return {"id":"event123","commence_time":KICKOFF,
      "home_team":"Atlanta Falcons","away_team":"Chicago Bears",
      "bookmakers":[{"key":book,"last_update":"2026-10-17T14:45:00Z",
        "markets":[{"key":"player_reception_yds","last_update":"2026-10-17T14:45:00Z",
          "outcomes":[{"name":"Over","description":player,"point":74.5,"price":-110},
            {"name":"Under","description":player,"point":74.5,"price":-110}]}]}]}

class Phase37Tests(unittest.TestCase):
    def test_offline_has_two_players_with_real_frozen_projections(self):
        r=offline_decisions(snapshot())
        self.assertEqual(r["player_rows"],2)
        self.assertEqual(r["fixtures"][0]["research_players"][0]["projected_receiving_yards"],80.)
        self.assertEqual(r["allocated_units"],0)
        self.assertEqual(r["qualified_singles"],[])
        self.assertEqual(r["market_audit"]["status"],"not_requested")
    def test_non_skill_removed(self):
        r=offline_decisions(snapshot(),{("ATL","gsis1"):"OT",("CHI","gsis2"):"WR"})
        self.assertEqual(r["non_skill_excluded"],1)
        self.assertEqual(r["player_rows"],1)
        self.assertEqual(r["fixtures"][0]["research_players"][0]["player_name"],"Rome Odunze")
    def test_authentic_matching_counts_without_exporting_odds(self):
        result=match_live_fanduel(snapshot(),data(),CAPTURE)
        self.assertEqual(result["counts"]["valid_fanduel_two_sided_pairs"],1)
        self.assertEqual(result["counts"]["unique_name_matched_players_with_pairs"],1)
        self.assertFalse(result["provider_id_player_verified"])
        self.assertFalse(result["raw_quote_rows_exported"])
        self.assertNotIn("Drake London",str(result))
        self.assertNotIn("74.5",str(result))
        self.assertEqual(result["qualified_singles"],0)
    def test_other_bookmaker_rejected(self):
        with self.assertRaises(ValueError):match_live_fanduel(snapshot(),data("draftkings"),CAPTURE)
    def test_unknown_player_never_matched(self):
        result=match_live_fanduel(snapshot(),data(player="Unlisted Player"),CAPTURE)
        self.assertEqual(result["counts"].get("valid_fanduel_two_sided_pairs",0),0)
        self.assertEqual(result["counts"]["unmatched_player_sides"],2)
    def test_postkickoff_capture_rejected(self):
        with self.assertRaises(ValueError):
            match_live_fanduel(snapshot(),data(),"2026-10-18T18:00:00Z")
    def test_html_research_only_no_offered_price(self):
        board=offline_decisions(snapshot())
        page=safe_html(board)
        self.assertIn("Drake London",page)
        self.assertIn("PASS",page)
        self.assertNotIn("74.5",page)
        self.assertNotIn("american_odds",page)
    def test_quoted_book_probabilities_still_unverified(self):
        board=offline_decisions(snapshot())
        for g in board["fixtures"]:
            for p in g["research_players"]:
                self.assertFalse(p["qualified"])
                self.assertIsNone(p["p_win_at_actual_fanduel_line"])
                self.assertIsNone(p["expected_roi"])
                self.assertEqual(p["units"],0)
    def test_api_must_be_explicit_opt_in(self):
        with patch("scripts.phase37_gameday_integration.fetch_json",
             side_effect=AssertionError("Never call Odds API offline")):
            offline_decisions(snapshot())
    def test_no_event_skips_paid_fanduel_request(self):
        with patch("scripts.phase37_gameday_integration.discover",return_value=[]),patch(
           "scripts.phase37_gameday_integration.fetch_json",
           side_effect=AssertionError("No paid events")):
            result=live_once(snapshot(),"synthetic")
        self.assertFalse(result["paid_event_quote_request_made"])
    def test_frozen_payload_modification_detected(self):
        bad=snapshot();bad["forecasts"][0]["receiving_yards"]=999
        with self.assertRaises(ValueError):offline_decisions(bad)
if __name__=="__main__":unittest.main()
