import unittest
from unittest.mock import patch
from scripts.phase36_evidence_chain import (
 provenance,paired_binary_dependence,freeze_private_quote_hash,phase36)
from test_phase32_market_matching import snapshot

def evidence():
    return {"source_kind":"nfl_official_gameday",
       "source_url":"https://www.nfl.com/","retrieved_at_utc":"2026-10-17T15:00:00Z",
       "kickoff_utc":"2026-10-18T17:00:00Z","event_id":"fixture1",
       "player_id":"gsis1","status":"ACTIVE","source_record_sha256":"a"*64}

class Phase36Tests(unittest.TestCase):
    def test_fake_official_active_never_certified(self):
        r=provenance(evidence(),asof="2026-10-17T16:00:00Z")
        self.assertFalse(r["usable_for_official_actives"])
        self.assertIn("source_authenticity_not_independently_attested",r["reasons"])
    def test_future_evidence_cannot_be_retroactively_valid(self):
        r=provenance(evidence(),asof="2026-10-17T14:00:00Z")
        self.assertIn("future_retrieval_time",r["reasons"])
    def test_quote_after_kickoff_rejected(self):
        row={"bookmaker":"fanduel","captured_at_utc":"2026-10-18T18:00:00Z",
             "kickoff_utc":"2026-10-18T17:00:00Z"}
        with self.assertRaises(ValueError):
            freeze_private_quote_hash([row],"2026-10-18T19:00:00Z")
    def test_private_quote_commitment_never_exposes_player_or_line(self):
        row={"bookmaker":"fanduel","captured_at_utc":"2026-10-17T15:00:00Z",
             "kickoff_utc":"2026-10-18T17:00:00Z",
             "player_name":"Example Receiver","american_odds":-110,
             "line":65.5}
        result=freeze_private_quote_hash([row],"2026-10-17T15:05:00Z")
        self.assertEqual(result["quote_count"],1)
        self.assertNotIn("Example Receiver",str(result))
        self.assertNotIn("65.5",str(result))
        self.assertFalse(result["raw_quotes_retained"])
    def test_other_bookmaker_quote_rejected(self):
        row={"bookmaker":"draftkings","captured_at_utc":"2026-10-17T15:00:00Z",
             "kickoff_utc":"2026-10-18T17:00:00Z"}
        with self.assertRaises(ValueError):
            freeze_private_quote_hash([row],"2026-10-17T15:05:00Z")
    def test_empty_historical_pairs_no_fake_probability(self):
        result=paired_binary_dependence([])
        self.assertIsNone(result["joint_hit_rate"])
        self.assertEqual(result["qualified_parlays"],0)
    def test_joint_probability_uses_pair_frequency_not_product(self):
        rows=[{"week":i%6+1,"historical_fixture_id":str(i),"a":i%2==0,"b":i%2==0} for i in range(150)]
        result=paired_binary_dependence(rows)
        self.assertEqual(result["joint_hit_rate"],.5)
        self.assertEqual(result["independence_baseline"],.25)
        self.assertTrue(result["not_out_of_sample_calibrated"])
        self.assertEqual(result["status"],"DESCRIPTIVE_DEPENDENCE_ONLY")
    def test_prevent_mismatched_binary_truth(self):
        with self.assertRaises(ValueError):
            paired_binary_dependence([{"week":1,"historical_fixture_id":"g","a":1,"b":True}])
    def test_sufficient_rows_but_insufficient_weeks(self):
        rows=[{"week":4,"historical_fixture_id":str(i),"a":True,"b":True} for i in range(200)]
        self.assertEqual(paired_binary_dependence(rows)["status"],
                         "INSUFFICIENT_INDEPENDENT_EVIDENCE")
    def test_week_slate_fails_closed_even_with_claimed_actives(self):
        result=phase36(snapshot(),1000,1,[evidence()])
        self.assertEqual(result["qualified_singles"],0)
        self.assertEqual(result["allocated_units"],0)
        self.assertEqual(result["official_game_day_active_records_authenticated"],0)
    def test_no_api_call_in_default_phase36(self):
        with patch("scripts.phase35_fanduel_portfolio.fetch_json",side_effect=AssertionError("no requests")):
            result=phase36(snapshot())
        self.assertEqual(result["decision"],"NO_BETS_EVIDENCE_INCOMPLETE")
if __name__=="__main__":unittest.main()
