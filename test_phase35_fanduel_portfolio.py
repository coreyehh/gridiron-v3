import unittest
from unittest.mock import patch
from scripts.phase35_fanduel_portfolio import (
 bankroll_config,validate_candidate,single_stake,validate_parlay,
 portfolio,review_fanduel,create_ledger,BOOK)
from scripts.phase34_decision_dashboard import build
from test_phase32_market_matching import snapshot,quotes,event,CAPTURE,KICKOFF

def valid_candidate():
    return {"selection_id":"test","event_id":"fixture1","player_id":"gsis1",
       "market":"receiving_yards","bookmaker":"fanduel",
       "same_book_two_sided_pair_validated":True,
       "snapshot_locked_before_offer":True,
       "player_identity_verified":True,
       "official_game_day_active_verified":True,
       "role_and_route_verified":True,
       "real_line_probability_independently_validated":True,
       "pregame_quote_fresh":True,"football_context_verified":True,
       "american_odds":-110,"p_win":.63}

class Phase35Tests(unittest.TestCase):
    def test_bankroll_unit_and_stake(self):
        a=bankroll_config(1000,1)
        self.assertEqual(a["unit_value"],10)
        self.assertEqual(a["total_stake_cap"],30)
        self.assertEqual(a["parlay_unit_caps"]["5"],.1)
    def test_invalid_bankroll_and_units_rejected(self):
        for b,u in ((-1,1),(0,1),(float("nan"),1),(1000,0),(1000,5)):
            with self.assertRaises(ValueError):bankroll_config(b,u)
    def test_no_live_player_verification_bets_not_allowed(self):
        x=valid_candidate()
        x["official_game_day_active_verified"]=False
        result=single_stake(x,bankroll_config())
        self.assertEqual(result["units"],0)
        self.assertIn("unverified_game_day_actives",result["reasons"])
    def test_no_fabricated_player_probability(self):
        x=valid_candidate();x["real_line_probability_independently_validated"]=False
        out=validate_candidate(x)
        self.assertFalse(out["qualified"])
        self.assertIn("unvalidated_real_line_probability",out["reasons"])
        self.assertIsNone(out["estimated_roi"])
    def test_fanduel_only_not_generic_book(self):
        x=valid_candidate();x["bookmaker"]="draftkings"
        self.assertFalse(validate_candidate(x)["qualified"])
    def test_bad_price_and_probability_cannot_promote(self):
        for prob,odds in ((None,-110),(True,-110),(2,-110),(.63,-90),(.63,None)):
            x=valid_candidate();x["p_win"]=prob;x["american_odds"]=odds
            self.assertFalse(validate_candidate(x)["qualified"])
    def test_conditional_kelly_is_capped(self):
        x=valid_candidate()
        s=single_stake(x,bankroll_config())
        self.assertEqual(s["decision"],"QUALIFIED_RESEARCH_PROPOSAL")
        self.assertLessEqual(s["units"],1.0)
        self.assertGreater(s["units"],0)
    def test_public_default_allocates_nothing(self):
        p=portfolio([],1000,1)
        self.assertEqual(p["total_units"],0)
        self.assertEqual(p["total_stake"],0)
        self.assertEqual(len(p["parlay_slots"]),4)
        self.assertEqual(p["qualified_parlays"]["5"],[])
    def test_no_sgp_price_cannot_invent_parlay(self):
        a=valid_candidate();b={**a,"player_id":"gsis2"}
        x=validate_parlay([a,b],joint_probability=.5,joint_model_validated=True,
            combined_american_odds=+300)
        self.assertFalse(x["eligible"])
        self.assertIn("no_verified_fanduel_combined_quote_or_acceptance",x["reasons"])
    def test_no_independence_multiplication_for_parlay(self):
        a=valid_candidate();b={**a,"player_id":"gsis2"}
        x=validate_parlay([a,b],combined_american_odds=+300,
            payout_source_verified=True,fanduel_acceptance_verified=True)
        self.assertFalse(x["eligible"])
        self.assertIn("no_validated_joint_distribution",x["reasons"])
    def test_duplicate_same_player_market_rejected(self):
        a=valid_candidate()
        x=validate_parlay([a,{**a,"selection_id":"other"}],combined_american_odds=300,
            joint_probability=.5,joint_model_validated=True,
            payout_source_verified=True,fanduel_acceptance_verified=True)
        self.assertFalse(x["eligible"])
        self.assertIn("duplicate_or_opposing_player_market",x["reasons"])
    def test_parlay_outside_two_to_five_rejected(self):
        x=valid_candidate()
        for n in (1,6):
            with self.assertRaises(ValueError):validate_parlay([{**x,"player_id":str(i)} for i in range(n)])
    def test_fanduel_same_book_valid_pair(self):
        snap=snapshot()
        offer=quotes()
        for row in offer:row["bookmaker"]=BOOK
        payload={"id":"event123","commence_time":KICKOFF,
         "home_team":"Atlanta Falcons","away_team":"Chicago Bears",
         "bookmakers":[{"key":"fanduel","last_update":"2026-10-17T14:45:00Z",
           "markets":[{"key":"player_reception_yds","last_update":"2026-10-17T14:45:00Z",
              "outcomes":[{"name":"Over","description":"Drake London","point":74.5,"price":-110},
                {"name":"Under","description":"Drake London","point":74.5,"price":-110}]}]}]}
        out=review_fanduel(snap,payload,CAPTURE)
        self.assertEqual(out["counts"]["valid_fanduel_pairs"],1)
        self.assertEqual(out["qualified_singles"],0)
        self.assertFalse(out["individual_book_quotes_published"])
        self.assertNotIn("74.5",str(out))
        self.assertNotIn("Drake London",str(out))
    def test_reject_other_books_even_if_fanduel_present(self):
        payload={"id":"event123","commence_time":KICKOFF,
         "home_team":"Atlanta Falcons","away_team":"Chicago Bears",
         "bookmakers":[{"key":"draftkings","markets":[]}]}
        with self.assertRaisesRegex(ValueError,"Non-FanDuel"):
            review_fanduel(snapshot(),payload,CAPTURE)
    def test_ledger_has_no_phantom_placed_bets(self):
        snap=snapshot()
        ledger=create_ledger(build(snap),portfolio([]))
        self.assertTrue(ledger["no_wagers_assumed_placed"])
        self.assertEqual(ledger["official_bets"],0)
        self.assertIsNone(ledger["realized_roi"])
        self.assertIn("audit_sha256",ledger)
    def test_no_api_called_in_portfolio(self):
        with patch("scripts.phase35_fanduel_portfolio.fetch_json",
          side_effect=AssertionError("No API permitted")):
            self.assertEqual(portfolio([])["total_units"],0)
if __name__=="__main__":unittest.main()
