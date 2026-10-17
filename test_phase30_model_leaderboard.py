import unittest
from scripts.phase30_model_leaderboard import (
 tournament,eligible_for_promotion,markdown,METRICS,CANDIDATES)
from scripts.phase28_snap_participation import conservative_join,validate_snap_frame
from test_phase23_role_model import sample
import pandas as pd

def synthetic():
    history,schedule=sample()
    roster=[{"team":club,"player_id":name+club,"player_name":label+" "+club}
      for club in ("BUF","LA") for name,label in
      (("wr","Receiver"),("rb","Runner"))]
    snaps=pd.DataFrame([
       {"season":2026,"week":w,"game_type":"REG","team":club,
        "player":label+" "+club,"offense_snaps":n,"offense_pct":.7}
       for club in ("BUF","LA") for name,label,n in
       (("wr","Receiver",40),("rb","Runner",20)) for w in (1,2,3,4)])
    joined=conservative_join(history,validate_snap_frame(snaps,2026),roster)
    return history,schedule,joined

class Phase30Tests(unittest.TestCase):
    def test_all_models_identical_player_cohort(self):
        h,s,j=synthetic()
        report=tournament(h,s,j,4,4)
        self.assertEqual(report["weeks"],[4])
        self.assertTrue(report["same_cohort_for_all_five_candidates"])
        for m in CANDIDATES:
            self.assertEqual([x["n"] for x in report["summary"][m]],
                             [report["player_games"]]*3)
        self.assertEqual(report["production_promotions"],0)
        self.assertIn("Paired forecasting",markdown(report))
    def test_future_week_outcomes_not_used_for_week4_features(self):
        h,s,j=synthetic()
        original=tournament(h,s,j,4,4)
        changed=h.copy()
        mask=(changed.season==2026)&(changed.week==4)&(changed.player_id=="wrBUF")
        changed.loc[mask,"receiving_yards"]=999.
        altered=tournament(changed,s,j,4,4)
        self.assertEqual(original["player_games"],altered["player_games"])
        self.assertNotEqual(original["summary"],altered["summary"])
    def test_short_sample_never_promotes(self):
        h,s,j=synthetic()
        report=tournament(h,s,j,4,4)
        self.assertTrue(all(not d["research_evidence_gate"]
           for d in report["promotion_gates"].values()))
    def test_apparent_improvement_with_tiny_sample_is_rejected(self):
        evidence={"candidate":"phase29","weeks":[4,5],
         "player_games":1000,"summary":{
           "phase23":[{"metric":k,"mae":10} for k in METRICS],
           "phase29":[{"metric":k,"mae":1} for k in METRICS]},
         "weekly_diagnostics":{"phase29":[
           {"week":4,"yards_improved":True},{"week":5,"yards_improved":True}]}}
        allowed,why=eligible_for_promotion(evidence)
        self.assertFalse(allowed)
        self.assertEqual(why,"insufficient_independent_games_or_weeks")
    def test_large_and_consistent_sample_still_needs_prospective(self):
        evidence={"candidate":"phase27","weeks":list(range(4,11)),
         "player_games":2100,"summary":{
            "phase23":[{"metric":k,"mae":10} for k in METRICS],
            "phase27":[{"metric":k,"mae":9} for k in METRICS]},
         "weekly_diagnostics":{"phase27":[
            {"week":n,"yards_improved":True} for n in range(4,11)]}}
        gate,reason=eligible_for_promotion(evidence)
        self.assertTrue(gate)
        self.assertIn("prospective_confirmation",reason)
if __name__=="__main__":unittest.main()
