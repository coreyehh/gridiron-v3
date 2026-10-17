import unittest
from scripts.phase38_official_calibration import (
 official_page_probe,evaluated_week_diagnostics,prospective_offer_gate,build)
from test_phase32_market_matching import snapshot

def sample_offer():
    return {"week":4,"fixture_id":"game1","player_id":"gsis1",
      "market":"receiving_yards","line":55.5,
      "quoted_at_utc":"2026-10-17T14:00:00Z",
      "captured_at_utc":"2026-10-17T14:05:00Z",
      "kickoff_utc":"2026-10-18T17:00:00Z",
      "outcome":1,"frozen_probability":.6,
      "bookmaker":"fanduel","source_authenticated":True}

class Phase38Tests(unittest.TestCase):
    def test_official_nfl_html_is_not_automatically_inactive_report(self):
        r=official_page_probe(lambda url:(200,b"<html>inactives</html>",url),
                 now="2026-10-17T16:00:00Z")
        self.assertTrue(r["source_reachable"])
        self.assertEqual(r["bytes_received"],22)
        self.assertFalse(r["official_active_status_verified"])
        self.assertEqual(r["validated_fixture_bound_gsis_inactive_entries"],0)
    def test_official_host_redirect_rejected(self):
        r=official_page_probe(lambda url:(200,b"secret","https://other.com/"))
        self.assertFalse(r["source_reachable"])
    def test_non200_inactive_source_never_fails_open(self):
        r=official_page_probe(lambda url:(403,b"Forbidden",url))
        self.assertFalse(r["official_active_status_verified"])
        self.assertFalse(r["source_reachable"])
    def test_official_inactive_html_checksum_deterministic(self):
        r=official_page_probe(lambda url:(200,b"same",url))
        self.assertEqual(len(r["raw_content_sha256"]),64)
    def test_historical_calibration_counts_weeks_separately(self):
        fake={"observed_player_games":529,"missing_box_rows_excluded":158,
          "scores":{"receptions":{"cases":1290,"weeks":[5],"brier":.1425,"ece":.0525},
           "receiving_yards":{"cases":1290,"weeks":[5],"brier":.1272,"ece":.0583}}}
        diag=evaluated_week_diagnostics(fake)
        self.assertEqual(diag["markets"]["receptions"]["independent_scored_weeks"],1)
        self.assertFalse(diag["markets"]["receptions"]["preliminary_week_gate_pass"])
        self.assertFalse(diag["prospective_real_fanduel_line_validation_pass"])
    def test_no_archived_offers_is_not_zero_roi(self):
        r=prospective_offer_gate([])
        self.assertIsNone(r["mean_brier_on_supplied_records"])
        self.assertEqual(r["qualified_singles"],0)
    def test_caller_supplied_attestation_never_certifies(self):
        r=prospective_offer_gate([sample_offer()])
        self.assertFalse(r["source_attestation_integrated"])
        self.assertFalse(r["prospective_fanduel_probability_calibration_verified"])
        self.assertEqual(r["observed_real_line_records_supplied"],1)
    def test_postgame_offers_rejected(self):
        x=sample_offer();x["captured_at_utc"]="2026-10-18T17:01:00Z"
        with self.assertRaises(ValueError):prospective_offer_gate([x])
    def test_missing_observation_not_counted_as_under(self):
        x=sample_offer();x["outcome"]=None
        with self.assertRaises(ValueError):prospective_offer_gate([x])
    def test_duplicate_offered_line_rejected(self):
        x=sample_offer()
        with self.assertRaises(ValueError):prospective_offer_gate([x,x])
    def test_different_bookmaker_rejected(self):
        x=sample_offer();x["bookmaker"]="draftkings"
        with self.assertRaises(ValueError):prospective_offer_gate([x])
    def test_frozen_week6_never_promotes_without_verified_inputs(self):
        r=build(snapshot())
        self.assertEqual(r["qualified_singles"],0)
        self.assertEqual(r["units_allocated"],0)
        self.assertEqual(r["qualified_parlays_by_leg_count"]["5"],0)
    def test_snapshot_tamper_protected(self):
        s=snapshot();s["forecasts"][0]["receptions"]=999
        with self.assertRaises(ValueError):build(s)
if __name__=="__main__":unittest.main()
