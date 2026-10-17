import unittest
import pandas as pd
from scripts.phase34_decision_dashboard import (
 build,markdown,webpage,player_status,position_lookup)
from test_phase32_market_matching import snapshot
from test_phase23_role_model import sample

class Phase34Tests(unittest.TestCase):
    def test_frozen_fixture_board_and_gates(self):
        snap=snapshot()
        r=build(snap)
        self.assertEqual(r["displayed_players"],2)
        self.assertEqual(r["qualified_bets"],0)
        self.assertFalse(r["official_actives_source_integrated"])
        self.assertFalse(r["calibration_real_book_lines_validated"])
        self.assertEqual(r["games"][0]["players"][0]["evidence_status"],"RESEARCH_ONLY")
        self.assertIn("Research only",markdown(r))
    def test_non_skill_position_filtered_from_dashboard(self):
        snap=snapshot()
        r=build(snap,{("ATL","gsis1"):"OT",("CHI","gsis2"):"WR"})
        self.assertEqual(r["filtered_non_skill_rows"],1)
        self.assertEqual(r["displayed_players"],1)
        self.assertEqual(r["games"][0]["players"][0]["player"],"Rome Odunze")
    def test_unknown_position_remains_unverified_not_confirmed(self):
        r=build(snapshot())
        self.assertEqual(r["players_without_position_confirmation"],2)
        self.assertTrue(all(p["position"]=="UNVERIFIED"
              for g in r["games"] for p in g["players"]))
    def test_fake_official_active_flag_never_qualifies(self):
        state,reasons=player_status({"confirmed_active":True},"WR",
            {"official_active_verified":True,"routes_verified":True})
        self.assertEqual(state,"RESEARCH_ONLY")
        self.assertIn("official_active_not_verified",reasons)
    def test_calibration_flag_cannot_promote_to_bet(self):
        r=build(snapshot(),calibration={"research_sample_sufficiency_gate":True},
                market_aggregate={"matched_valid_two_sided_pairs":100})
        self.assertTrue(r["calibration_historical_sufficiency_passed"])
        self.assertFalse(r["individual_current_book_lines_available"])
        self.assertEqual(r["qualified_bets"],0)
        self.assertTrue(all(not p["qualified_play"]
                      for g in r["games"] for p in g["players"]))
    def test_html_escapes_untrusted_player_fields(self):
        x=snapshot()
        x["forecasts"][0]["player_name"]='<script>alert("x")</script>'
        from scripts.phase31_accountability import digest
        x["payload_sha256"]=digest({k:v for k,v in x.items() if k!="payload_sha256"})
        page=webpage(build(x))
        self.assertNotIn('<script>',page)
        self.assertIn("&lt;script&gt;",page)
        self.assertNotIn("Odds API",page)
    def test_history_position_uses_only_prior_week(self):
        h,s=sample()
        base=position_lookup(h,4)
        changed=h.copy()
        changed.loc[(changed.season==2026)&(changed.week==4),"position"]="OT"
        self.assertEqual(base,position_lookup(changed,4))
    def test_altered_projection_rejected_due_to_snapshot_integrity(self):
        x=snapshot()
        x["forecasts"][0]["receiving_yards"]=999.
        with self.assertRaisesRegex(ValueError,"hash mismatch"):
            build(x)
    def test_no_real_player_prices_or_ev_in_json(self):
        data=build(snapshot())
        self.assertEqual(data["qualified_bets"],0)
        self.assertFalse(data["individual_current_book_lines_available"])
        for game in data["games"]:
            for player in game["players"]:
                self.assertNotIn("american_odds",player)
                self.assertNotIn("bookmaker_name",player)
                self.assertNotIn("offered_line",player)
                self.assertIsNone(player["bookmaker_line_specific_probability"])
                self.assertIsNone(player["expected_roi"])
                self.assertFalse(player["qualified_play"])
if __name__=="__main__":unittest.main()
