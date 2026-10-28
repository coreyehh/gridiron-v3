import unittest
from datetime import datetime,timezone,timedelta
from scripts.wager_approval_gate import decide
NOW=datetime(2026,10,26,23,tzinfo=timezone.utc)
def candidate(**updates):
    d={"fixture_id":"g","player_id":"p","market":"receiving_yards",
       "selection":"over","book":"test-book","line":50.5,
       "decimal_odds":2.0,"model_probability":0.56,
       "market_observed_at_utc":(NOW-timedelta(minutes=5)).isoformat(),
       "official_active_verified":True,"role_verified":True,
       "opponent_adjusted":True,"probabilities_calibrated":True,
       "price_source_authenticated":True,"fixture_not_started_verified":True,
       "human_approved":True}
    d.update(updates)
    return d
class GateTests(unittest.TestCase):
    def test_missing_verification_blocks(self):
        x=decide(candidate(official_active_verified=False),asof_utc=NOW)
        self.assertIn("ACTIVE_STATUS_UNVERIFIED",x["reasons"])
    def test_uncalibrated_blocks(self):
        x=decide(candidate(probabilities_calibrated=False),asof_utc=NOW)
        self.assertIn("PROBABILITY_CALIBRATION_UNVERIFIED",x["reasons"])
    def test_unverified_price_blocks(self):
        x=decide(candidate(price_source_authenticated=False),asof_utc=NOW)
        self.assertIn("SPORTSBOOK_PRICE_UNVERIFIED",x["reasons"])
    def test_negative_ev_blocks(self):
        x=decide(candidate(model_probability=0.4),asof_utc=NOW)
        self.assertIn("NON_POSITIVE_EXPECTED_VALUE",x["reasons"])
    def test_future_price_blocks(self):
        x=decide(candidate(market_observed_at_utc=(NOW+timedelta(minutes=1)).isoformat()),asof_utc=NOW)
        self.assertIn("INVALID_MARKET_ASOF",x["reasons"])
    def test_approval_required(self):
        x=decide(candidate(human_approved=False),asof_utc=NOW)
        self.assertIn("NOT_APPROVED_FOR_WAGER",x["reasons"])
    def test_all_gates_yield_review_only(self):
        x=decide(candidate(),asof_utc=NOW)
        self.assertEqual(x["status"],"ELIGIBLE_FOR_HUMAN_REVIEW")
        self.assertEqual(x["approved_units"],0)
        self.assertFalse(x["wager_submitted"])
if __name__=="__main__":unittest.main()
