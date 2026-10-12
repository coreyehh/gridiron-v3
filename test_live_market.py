import unittest
from scripts.live_market import normalize, implied, summarize

def fixture():
    return {
      "id":"event1","commence_time":"2026-10-18T17:00:00Z",
      "home_team":"CIN","away_team":"BAL",
      "bookmakers":[{"key":"fanduel","last_update":"2026-10-18T12:00:00Z",
         "markets":[{"key":"player_receptions","last_update":"2026-10-18T12:00:00Z",
           "outcomes":[
              {"name":"Over","description":"Example RB","point":3.5,"price":-110},
              {"name":"Under","description":"Example RB","point":3.5,"price":-110}]}]}]
    }
class MarketTests(unittest.TestCase):
    def test_market_prices_and_guardrails(self):
        rows=normalize(fixture(),"2026-10-18T12:02:00Z")
        self.assertEqual(len(rows),2)
        self.assertEqual({x["side"] for x in rows},{"over","under"})
        self.assertAlmostEqual(implied(-110),110/210)
        self.assertTrue(all(x["estimated_roi"] is None and x["decision"]=="INSUFFICIENT_DATA" for x in rows))
        self.assertTrue(all(not x["player_id_verified"] for x in rows))
        self.assertEqual(summarize(rows,"2026-10-18T12:02:00Z")["bets_qualified"],0)
    def test_kickoff_rejected(self):
        with self.assertRaises(ValueError):
            normalize(fixture(),"2026-10-18T17:00:00Z")
    def test_future_bookmaker_time_rejected(self):
        payload=fixture()
        payload["bookmakers"][0]["markets"][0]["last_update"]="2026-10-18T12:05:00Z"
        with self.assertRaises(ValueError):
            normalize(payload,"2026-10-18T12:02:00Z")
    def test_duplicate_quote_fails(self):
        payload=fixture()
        payload["bookmakers"][0]["markets"][0]["outcomes"].append(
            {"name":"Over","description":"Example RB","point":3.5,"price":-110})
        with self.assertRaises(ValueError):
            normalize(payload,"2026-10-18T12:02:00Z")
    def test_market_requires_player_name(self):
        payload=fixture()
        payload["bookmakers"][0]["markets"][0]["outcomes"][0].pop("description")
        self.assertEqual(len(normalize(payload,"2026-10-18T12:02:00Z")),1)
    def test_bad_price_rejected(self):
        with self.assertRaises(ValueError): implied(-90)
if __name__=="__main__":unittest.main()
