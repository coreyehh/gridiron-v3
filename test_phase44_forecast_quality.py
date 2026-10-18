import unittest,copy
from datetime import datetime,timezone
from scripts.phase44_forecast_quality import quality,audit,private_compare,run,require_ledger
from scripts.phase31_accountability import canonical,digest
from test_phase43_remaining_week6 import schedule,history
from scripts.phase43_remaining_week6 import build_remaining
import hashlib

def snap():
    roster=[{"team":"ATL","player_id":"p1","player_name":"Synthetic QB","position":"QB"}]
    result,_=build_remaining(schedule(),history(),roster,
                     datetime(2026,10,18,16,0,tzinfo=timezone.utc),{"input":"synthetic"})
    return result

def ledger(s):
    q={"fixture_id":"2026-W06-CHI-at-ATL","team":"ATL","player_name":"Synthetic QB",
       "market":"receiving_yards","fanduel_line":44.5,
       "over_american_odds":-110,"under_american_odds":-110,
       "frozen_projection":39.2,"over_quote_updated_utc":"2026-10-18T15:30:00Z",
       "under_quote_updated_utc":"2026-10-18T15:30:00Z"}
    d={"version":"phase40-prospective-offer-forecast-outcome-ledger-v1",
       "entries":[q],"official_bets":0}
    d["lock_sha256"]=hashlib.sha256(canonical(d).encode()).hexdigest()
    return d

class Phase44Tests(unittest.TestCase):
    def test_public_flags_never_claim_actives(self):
        rows,report=audit(snap())
        self.assertEqual(report["qualified_bets"],0)
        self.assertFalse(report["official_player_active_verified"])
        self.assertTrue(all(not r["bet_qualified"] and r["stake_units"]==0 for r in rows))
    def test_future_lock_after_quote_disqualifies_comparison(self):
        s=snap()
        rows,summary=private_compare(s,ledger(s))
        self.assertEqual(len(rows),1)
        self.assertFalse(rows[0]["phase43_lock_before_bookmaker_quote"])
        self.assertIsNone(rows[0]["phase43_new_market_forecast"])
        self.assertIsNone(rows[0]["prospective_edge"])
        self.assertEqual(summary["phase43_lock_after_original_market_quote"],1)
    def test_lock_before_quote_still_no_receiving_forecast(self):
        s=snap();l=ledger(s)
        l["entries"][0]["over_quote_updated_utc"]="2026-10-18T16:10:00Z"
        l["entries"][0]["under_quote_updated_utc"]="2026-10-18T16:10:00Z"
        l["lock_sha256"]=hashlib.sha256(canonical({k:v for k,v in l.items() if k!="lock_sha256"}).encode()).hexdigest()
        rows,summary=private_compare(s,l)
        self.assertTrue(rows[0]["phase43_lock_before_bookmaker_quote"])
        self.assertFalse(rows[0]["qualified_bet"])
        self.assertEqual(summary["phase43_lock_before_market_quote"],1)
    def test_exact_fixture_and_team_name_required(self):
        s=snap();l=ledger(s)
        l["entries"][0]["team"]="CHI"
        l["lock_sha256"]=hashlib.sha256(canonical({k:v for k,v in l.items() if k!="lock_sha256"}).encode()).hexdigest()
        rows,stats=private_compare(s,l)
        self.assertFalse(rows)
        self.assertEqual(stats["missing_or_ambiguous_player"],1)
    def test_tampered_encrypted_ledger_digest_rejected(self):
        s=snap();l=ledger(s);l["entries"][0]["fanduel_line"]=999
        with self.assertRaises(ValueError):private_compare(s,l)
    def test_extreme_rushing_flags_are_flags_not_picks(self):
        s=snap();r=copy.deepcopy(s["forecasts"][0])
        r["position"]="RB";r["point_projections"]["rushing_yards"]=135
        q=quality(r)
        self.assertIn("EXTREME_RUSHING_YARDS_ESTIMATE",q["risk_reasons"])
        self.assertEqual(q["decision"],"HOLD_RESEARCH_ONLY")
    def test_zero_scored_td_is_not_a_true_zero(self):
        s=snap();r=copy.deepcopy(s["forecasts"][0])
        r["point_projections"]["td_count_mean"]=0
        q=quality(r)
        self.assertIn("ZERO_OBSERVED_TD_RATE_NOT_ZERO_TRUE_CHANCE",q["risk_reasons"])
    def test_public_summary_no_quote_prices(self):
        s=snap();l=ledger(s)
        qa,comparison,report=run(s,l)
        self.assertNotIn("44.5",str(report))
        self.assertNotIn("-110",str(report))
        self.assertNotIn("Synthetic QB",str(report))
        self.assertEqual(len(comparison),1)
        self.assertEqual(report["comparison"]["phase43_sportsbook_edges_qualified"],0)
    def test_same_snapshot_unchanged(self):
        s=snap();expected=s["payload_sha256"]
        run(s,ledger(s))
        self.assertEqual(s["payload_sha256"],expected)
        self.assertEqual(digest({k:v for k,v in s.items() if k!="payload_sha256"}),expected)
if __name__=="__main__":unittest.main()
