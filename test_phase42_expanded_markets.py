import unittest
from cryptography.fernet import Fernet
from scripts.phase42_expanded_markets import (
 CATEGORIES,supported,player_of,extract,strict_groups,merge,audit)
from test_phase32_market_matching import snapshot,event,CAPTURE
def sample():
    e=event()
    return {"id":e["id"],"commence_time":e["commence_time"],
      "home_team":e["home_team"],"away_team":e["away_team"],
      "bookmakers":[{"key":"fanduel","markets":[
       {"key":"player_pass_yds","last_update":"2026-10-17T14:45:00Z",
        "outcomes":[{"name":"Over","description":"Drake London","point":245.5,"price":-110},
                    {"name":"Under","description":"Drake London","point":245.5,"price":-110}]},
       {"key":"player_rush_yds","last_update":"2026-10-17T14:45:00Z",
        "outcomes":[{"name":"Over","description":"Rome Odunze","point":44.5,"price":-110},
                    {"name":"Under","description":"Rome Odunze","point":44.5,"price":-110}]},
       {"key":"player_anytime_td","last_update":"2026-10-17T14:45:00Z",
        "outcomes":[{"name":"Drake London","price":125},
                    {"name":"Yes","description":"Rome Odunze","price":150}]},
       {"key":"player_2plus_tds","last_update":"2026-10-17T14:45:00Z",
        "outcomes":[{"name":"Drake London","price":650}]},
       {"key":"player_3plus_tds","last_update":"2026-10-17T14:45:00Z",
        "outcomes":[{"name":"Drake London","price":1800}]}]}]}
class Phase42Tests(unittest.TestCase):
    def test_markets_cover_pass_rush_multi_td(self):
        m=supported(["passing","rushing","touchdowns"])
        self.assertIn("player_pass_tds",m)
        self.assertIn("player_rush_attempts",m)
        self.assertIn("player_2plus_tds",m)
        self.assertIn("player_3plus_tds",m)
    def test_td_name_and_yes_form(self):
        self.assertEqual(player_of({"name":"Drake London"},"anytime_touchdown"),("Drake London","yes"))
        self.assertEqual(player_of({"name":"Yes","description":"Rome Odunze"},"anytime_touchdown"),("Rome Odunze","yes"))
        self.assertEqual(player_of({"name":"No"},"anytime_touchdown"),(None,None))
    def test_source_quotes_and_unmodeled_projections(self):
        rows,meta=extract(sample(),CAPTURE,snapshot(),event())
        self.assertEqual(len(rows),8)
        self.assertEqual(meta["counts"]["accepted_outcome_sides"],8)
        self.assertTrue(all(x["projection"] is None for x in rows))
        self.assertTrue(all(x["estimated_ev"] is None and not x["qualified"] for x in rows))
        self.assertTrue(all(x["player_identity_provider_verified"] is False for x in rows))
    def test_two_sided_pass_rush_and_single_td_prices(self):
        rows,_=extract(sample(),CAPTURE,snapshot(),event())
        kept,rejected=strict_groups(rows)
        self.assertEqual(len(kept),8)
        self.assertEqual(rejected,{})
        self.assertEqual(len([x for x in kept if x["category"]=="touchdowns"]),4)
    def test_unmatched_quarterback_quote_is_preserved_without_invented_id(self):
        p=sample()
        p["bookmakers"][0]["markets"][0]["outcomes"]=[
            {"name":"Over","description":"Synthetic Quarterback","point":245.5,"price":-110},
            {"name":"Under","description":"Synthetic Quarterback","point":245.5,"price":-110}]
        rows,meta=extract(p,CAPTURE,snapshot(),event())
        qb=[r for r in rows if r["player_name"]=="Synthetic Quarterback"]
        self.assertEqual(len(qb),2)
        self.assertTrue(all(r["player_id"] is None and r["team"] is None for r in qb))
        self.assertEqual(meta["counts"]["unmatched_player_evidence_retained"],2)
        self.assertEqual(len(strict_groups(rows)[0]),8)
    def test_mixed_bookmaker_rejected(self):
        p=sample();p["bookmakers"].append({"key":"draftkings","markets":[]})
        with self.assertRaises(ValueError):extract(p,CAPTURE,snapshot(),event())
    def test_quote_older_than_locked_is_skipped(self):
        p=sample()
        for m in p["bookmakers"][0]["markets"]:
            m["last_update"]="2026-10-17T12:45:00Z"
        rows,meta=extract(p,CAPTURE,snapshot(),event())
        self.assertFalse(rows)
        self.assertEqual(meta["counts"]["stale_or_prelock_markets"],5)
    def test_pre_kickoff_enforced(self):
        with self.assertRaises(ValueError):extract(sample(),"2026-10-18T19:00:00Z",snapshot(),event())
    def test_no_leak_from_offline_audit(self):
        combined,safe=audit(snapshot(),live=False)
        self.assertEqual(safe["new_event_quote_requests"],0)
        self.assertEqual(safe["new_pass_rush_td_quote_sides"],0)
        self.assertEqual(safe["official_bets"],0)
        self.assertNotIn("Drake London",str(safe))
    def test_preserve_original_receiving_pairs(self):
        s=snapshot()
        older={"entries":[{"fixture_id":"2026-W06-CHI-at-ATL","market":"receiving_yards",
              "fanduel_line":74.5}],"frozen_snapshot_sha256":s["payload_sha256"]}
        combined=merge(s,older,[])
        self.assertEqual(combined["prior_receiving_pairs"],1)
        self.assertEqual(combined["original_receiving_entries"],older["entries"])
    def test_duplicate_category_rejected(self):
        with self.assertRaises(ValueError):supported(["passing","passing"])
    def test_no_paid_api_with_zero_event_cap(self):
        with self.assertRaises(ValueError):
            audit(snapshot(),live=True,max_events=0,key=Fernet.generate_key().decode(),
                  odds_key="synthetic")
    def test_two_sided_market_without_under_is_not_a_pair(self):
        rows,_=extract(sample(),CAPTURE,snapshot(),event())
        rows=[x for x in rows if not(x["market"]=="passing_yards" and x["side"]=="under")]
        kept,counts=strict_groups(rows)
        self.assertEqual(len(kept),6)
        self.assertEqual(counts["missing_or_ambiguous_two_sided_market"],1)
if __name__=="__main__":unittest.main()
