import unittest
from datetime import datetime,timezone,timedelta
from scripts.pregame_availability_gate import qualify
NOW=datetime(2026,10,26,22,tzinfo=timezone.utc)
P={"player_id":"p1","team":"CIN"}
F={"id":"2026-W08-CIN-at-BAL"}
def record(**changes):
    r={"player_id":"p1","team":"CIN","fixture_id":F["id"],
       "status":"ACTIVE","source":"official-example","source_record_id":"rec-1",
       "source_type":"OFFICIAL_GAME_DAY_INACTIVES",
       "observed_at_utc":(NOW-timedelta(hours=1)).isoformat()}
    r.update(changes)
    return r
class TestAvailability(unittest.TestCase):
    def test_missing_record_blocks(self):
        self.assertEqual(qualify(P,F,None,asof_utc=NOW)["status"],"NO_BET")
    def test_roster_listing_is_not_actives(self):
        x=qualify(P,F,record(source_type="ROSTER"),asof_utc=NOW)
        self.assertIn("NOT_OFFICIAL_GAME_DAY_CONFIRMATION",x["reasons"])
    def test_wrong_player_blocks(self):
        x=qualify(P,F,record(player_id="someone-else"),asof_utc=NOW)
        self.assertIn("PLAYER_TEAM_OR_FIXTURE_MISMATCH",x["reasons"])
    def test_future_report_blocks(self):
        x=qualify(P,F,record(observed_at_utc=(NOW+timedelta(minutes=1)).isoformat()),asof_utc=NOW)
        self.assertIn("EVIDENCE_AFTER_LOCK_OR_UNTIMESTAMPED",x["reasons"])
    def test_out_blocks(self):
        x=qualify(P,F,record(status="OUT"),asof_utc=NOW)
        self.assertIn("NOT_OFFICIALLY_CONFIRMED_ACTIVE",x["reasons"])
    def test_official_active_still_needs_role_and_price(self):
        x=qualify(P,F,record(),asof_utc=NOW)
        self.assertTrue(x["official_active_evidence_complete"])
        self.assertEqual(x["approved_units"],0)
        self.assertIn("STARTING_ROLE_AND_MARKET_MODEL_NOT_CERTIFIED",x["reasons"])
if __name__=="__main__":unittest.main()
