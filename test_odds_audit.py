import csv
import tempfile
import unittest
from pathlib import Path
from scripts.odds_audit import audit, normalize_quotes, probability_break_even, profit_per_dollar

def quote(**overrides):
    result={
        "source_id":"verified-provider-snapshot","event_id":"event-abc",
        "player_id":"00-0031234","season":"2025","week":"3",
        "market":"receptions","side":"over","line":"4.5",
        "american_odds":"-110","bookmaker":"example_book",
        "quoted_at_utc":"2025-09-20T12:00:00Z",
        "kickoff_at_utc":"2025-09-21T17:00:00Z",
        "provider_name":"example_historical_provider"}
    result.update(overrides)
    return result

class OddsAuditTests(unittest.TestCase):
    def test_mixed_price_math(self):
        self.assertAlmostEqual(probability_break_even(-110),110/210)
        self.assertAlmostEqual(probability_break_even(125),100/225)
        self.assertAlmostEqual(profit_per_dollar(-110),100/110)
        self.assertAlmostEqual(profit_per_dollar(125),1.25)
    def test_valid_pregame_quote(self):
        rows=normalize_quotes([quote()])
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["line"],4.5)
    def test_kickoff_and_future_quotes_blocked(self):
        for time in ("2025-09-21T17:00:00Z","2025-09-22T17:00:00Z"):
            with self.assertRaises(ValueError):
                normalize_quotes([quote(quoted_at_utc=time)])
    def test_unrecognized_market_and_ambiguous_odds_rejected(self):
        for change in ({"market":"anytime_td"},{"american_odds":"-110.5"},
                       {"line":"NaN"},{"quoted_at_utc":"2025-09-20T12:00:00-04:00"}):
            with self.assertRaises(ValueError):
                normalize_quotes([quote(**change)])
    def test_duplicate_quotes_rejected(self):
        with self.assertRaises(ValueError):
            normalize_quotes([quote(),quote()])
    def test_no_quotes_means_no_roi_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            x=audit(None,Path(tmp)/"audit.json")
            self.assertEqual(x["historical_quotes_validated"],0)
            self.assertFalse(x["backtested_roi_available"])
    def test_quote_file_does_not_publish_row_details(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/"odds.csv"
            with file.open("w",newline="") as f:
                w=csv.DictWriter(f,fieldnames=list(quote()))
                w.writeheader()
                w.writerow(quote())
            result=audit(file,Path(tmp)/"audit.json")
            self.assertEqual(result["historical_quotes_validated"],1)
            self.assertNotIn("event-abc",(Path(tmp)/"audit.json").read_text())

if __name__=="__main__":
    unittest.main()
