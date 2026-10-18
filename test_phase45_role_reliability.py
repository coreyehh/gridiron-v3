import unittest,copy
from datetime import datetime,timezone
import pandas as pd
from scripts.phase45_role_reliability import historical_role
from scripts.phase43_remaining_week6 import build_remaining
from test_phase43_remaining_week6 import schedule,history
def sample():
    roster=[{"team":"ATL","player_id":"p1","player_name":"Synthetic QB","position":"QB"}]
    snap,_=build_remaining(schedule(),history(),roster,
       datetime(2026,10,18,16,0,tzinfo=timezone.utc),{"synthetic":"yes"})
    h=history();h['targets']=0\n    return snap,h
class Phase45Tests(unittest.TestCase):
    def test_future_player_boxes_excluded_from_usage(self):
        s,h=sample()
        audits,report=historical_role(s,h)
        self.assertEqual(report["latest_2026_week_used"],5)
        self.assertEqual(report["target_week_box_rows_used"],0)
        self.assertEqual(report["approved_bets"],0)
    def test_all_remain_unverified_and_never_approved(self):
        s,h=sample();audits,report=historical_role(s,h)
        self.assertTrue(all(not a["official_active_verified"] for a in audits))
        self.assertTrue(all(a["decision"]=="ROLE_UNVERIFIED_NO_BET" for a in audits))
    def test_recent_usage_cannot_use_target_week(self):
        s,h=sample();a,_=historical_role(s,h)
        self.assertTrue(all(z["week"]<6 for x in a for z in x["historical_weekly_usage"]))
    def test_zero_td_flag_not_inactive(self):
        s,h=sample();a,_=historical_role(s,h)
        self.assertIn("ZERO_OBSERVED_TDS_DO_NOT_PROVE_ZERO_SCORE_CHANCE",a[0]["reason_codes"])
        self.assertNotIn("PLAYER_VERIFIED_INACTIVE",a[0]["reason_codes"])
    def test_multiple_qbs_need_starter_confirmation(self):
        s,h=sample();x=copy.deepcopy(s["forecasts"][0]);x["player_id"]="p2"
        x["player_name"]="Other QB"
        s["forecasts"].append(x)
        from scripts.phase31_accountability import digest
        s["payload_sha256"]=digest({k:v for k,v in s.items() if k!="payload_sha256"})
        a,_=historical_role(s,h)
        self.assertEqual(len(a),2)
        self.assertTrue(all("MULTIPLE_HISTORICAL_QB_CANDIDATES_NO_STARTER_CONFIRMED" in z["reason_codes"] for z in a))
    def test_missing_player_box_not_zero(self):
        s,h=sample()
        h=h[~((h.season==2026)&(h.week.isin([4,5])))].copy()
        a,_=historical_role(s,h)
        self.assertIn("NO_RECENT_PLAYER_BOX_OBSERVATION",a[0]["reason_codes"])
    def test_snapshot_tampering_is_rejected(self):
        s,h=sample();s["forecasts"][0]["player_name"]="Altered"
        with self.assertRaises(ValueError):historical_role(s,h)
    def test_public_audit_no_book_prices_or_api(self):
        s,h=sample();a,r=historical_role(s,h)
        self.assertEqual(r["new_bookmaker_requests"],0)
        self.assertEqual(r["units"],0)
        self.assertNotIn("american_odds",str(a))
if __name__=="__main__":unittest.main()
