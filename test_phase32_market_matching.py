import unittest
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from scripts.phase31_accountability import digest
from scripts.phase32_market_matching import (
 selected_fixture,matched_forecasts,compare,run,discover,VERSION)

LOCK="2026-10-17T13:00:00+00:00"
CAPTURE="2026-10-17T15:00:00Z"
KICKOFF="2026-10-18T17:00:00Z"
def snapshot():
    f={"id":"2026-W06-CHI-at-ATL","home":"ATL","away":"CHI",
       "gameday":"2026-10-18","player_forecasts":2,"kickoff_time_verified":False}
    rows=[]
    for pid,name,club in [("gsis1","Drake London","ATL"),("gsis2","Rome Odunze","CHI")]:
        rows.append({"fixture_id":f["id"],"week":6,"team":club,
          "player_id":pid,"player_name":name,
          "model":"phase23-player-role-with-phase20-volume",
          "targets":7.0,"receptions":5.0,"receiving_yards":80.0})
    x={"season":2026,"week":6,"created_at_utc":LOCK,
       "model":"phase23-player-role-with-phase20-volume",
       "fixtures":[f],"forecasts":rows}
    x["payload_sha256"]=digest(x)
    return x
def event():
    return {"id":"event123","home_team":"Atlanta Falcons","away_team":"Chicago Bears",
      "commence_time":KICKOFF}
def quotes():
    return [{
        "event_id":"event123","market":"receiving_yards",
        "side":side,"player_display_name":"Drake London",
        "bookmaker":"book-one","kickoff_utc":KICKOFF,
        "quoted_at_utc":"2026-10-17T14:45:00Z",
        "captured_at_utc":CAPTURE,"line":74.5,
        "american_odds":-110
    } for side in ("over","under")]

class Phase32Tests(unittest.TestCase):
    def test_offline_cannot_use_any_odds_api(self):
        with patch("scripts.phase32_market_matching.fetch_json",
                   side_effect=AssertionError("MUST NOT CALL")):
            r=run(snapshot())
        self.assertFalse(r["live_event_quote_request_made"])
        self.assertEqual(r["qualified_bets"],0)
    def test_exact_frozen_fixture_match(self):
        self.assertEqual(selected_fixture(snapshot(),event())["id"],"2026-W06-CHI-at-ATL")
    def test_rejects_wrong_event_and_dates(self):
        e=event();e["home_team"]="New York Jets"
        with self.assertRaises(ValueError):selected_fixture(snapshot(),e)
        e=event();e["commence_time"]="2026-10-23T17:00:00Z"
        with self.assertRaises(ValueError):selected_fixture(snapshot(),e)
    def test_real_line_comparison_is_aggregate_not_bet(self):
        r=compare(snapshot(),event(),quotes(),CAPTURE)
        self.assertEqual(r["counts"]["matched_valid_two_sided_pairs"],1)
        self.assertEqual(r["counts"]["projection_above_line"],1)
        self.assertFalse(r["market_rows_published"])
        self.assertFalse(r["matched_real_line_probabilities_calibrated"])
        self.assertEqual(r["qualified_bets"],0)
        self.assertNotIn("Drake London",str(r))
        self.assertNotIn("74.5",str(r))
        self.assertNotIn("book-one",str(r))
    def test_book_quote_before_freeze_cannot_be_marked_post_lock(self):
        prior=quotes()
        for r in prior:r["quoted_at_utc"]="2026-10-17T12:59:00Z"
        a=compare(snapshot(),event(),prior,CAPTURE)
        self.assertEqual(a["counts"]["quote_source_predates_frozen_lock"],2)
        self.assertEqual(a["counts"].get("book_source_timestamp_after_lock",0),0)
        self.assertEqual(a["qualified_bets"],0)
    def test_unpaired_market_is_not_a_valid_pair(self):
        a=compare(snapshot(),event(),quotes()[:1],CAPTURE)
        self.assertEqual(a["counts"].get("matched_valid_two_sided_pairs",0),0)
    def test_ambiguous_frozen_name_cannot_match(self):
        x=snapshot()
        duplicate=dict(x["forecasts"][0]);duplicate["player_id"]="gsis3"
        x["forecasts"].append(duplicate);x["payload_sha256"]=digest({k:v for k,v in x.items() if k!="payload_sha256"})
        a=compare(x,event(),quotes(),CAPTURE)
        self.assertEqual(a["ambiguous_snapshot_names"],1)
        self.assertEqual(a["counts"].get("matched_valid_two_sided_pairs",0),0)
    def test_prequote_clock(self):
        x=snapshot();x["created_at_utc"]="2026-10-18T18:00:00+00:00"
        x["payload_sha256"]=digest({k:v for k,v in x.items() if k!="payload_sha256"})
        with self.assertRaises(ValueError):selected_fixture(x,event())
    def test_no_purchases_without_explicit_live(self):
        with patch("scripts.phase32_market_matching.fetch_json",
          side_effect=AssertionError("must not spend")):
            self.assertEqual(run(snapshot(),False,key="dummy")["status"],"offline_no_credits")
    def test_unknown_team_name_does_not_match(self):
        e=event();e["away_team"]="University of Chicago"
        with self.assertRaises(ValueError):selected_fixture(snapshot(),e)
if __name__=="__main__":unittest.main()
