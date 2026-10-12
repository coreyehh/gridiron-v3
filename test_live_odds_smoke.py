import unittest
from unittest.mock import patch
from scripts.live_odds_smoke import summarize,check

class LiveOddsTests(unittest.TestCase):
    def test_only_counts_configured_markets(self):
        payload={"bookmakers":[
          {"key":"draftkings","markets":[
            {"key":"player_receptions","outcomes":[{"name":"Over","price":-110}]},
            {"key":"h2h","outcomes":[{"name":"A","price":100}]}]},
          {"key":"unknown_book","markets":[{"key":"player_reception_yds","outcomes":[]}]}
        ]}
        p,n=summarize(payload,{"player_receptions","player_reception_yds"})
        self.assertEqual(n,1)
        self.assertEqual(p["draftkings"]["markets"],["player_receptions"])
        self.assertNotIn("h2h",p["draftkings"]["markets"])
    @patch("scripts.live_odds_smoke.fetch_json")
    def test_discovery_only_never_calls_paid_endpoint(self,fetch):
        fetch.return_value=([{"id":"xyz","commence_time":"2026-10-20T12:00:00Z"}],
                            {"x-requests-remaining":"500"})
        r=check("fake-key",enable_odds=False)
        self.assertFalse(r["odds_request_made"])
        self.assertEqual(fetch.call_count,1)
    @patch("scripts.live_odds_smoke.fetch_json")
    def test_one_game_one_odds_call(self,fetch):
        fetch.side_effect=[
          ([{"id":"xyz","commence_time":"2026-10-20T12:00:00Z"}],{}),
          ({"bookmakers":[{"key":"fanduel","markets":[{"key":"player_receptions",
             "outcomes":[{"name":"Over","price":-115}]}]}]},
           {"x-requests-last":"1"})]
        r=check("fake-key",enable_odds=True)
        self.assertEqual(fetch.call_count,2)
        self.assertEqual(r["outcome_count"],1)
        self.assertTrue(r["odds_request_made"])
        self.assertFalse(r["roi_verified"])
        self.assertNotIn("xyz",str(r))
    def test_invalid_regions_rejected(self):
        with self.assertRaises(ValueError):check("fake",region="eu")
if __name__=="__main__":unittest.main()
