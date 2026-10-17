import unittest
import pandas as pd
from scripts.phase22_script_intervals import (
    corrected, interval, pregame_state, evaluate, markdown, MIN_CORRECTION, MIN_INTERVAL)
from test_phase21_walkforward import fixture

class Phase22Tests(unittest.TestCase):
    def test_shrinkage_has_minimum_history(self):
        previous=[{"metric":"pass_attempts","state":"favored","error":15.} for _ in range(MIN_CORRECTION-1)]
        val,n=corrected(30,"favored","pass_attempts",previous)
        self.assertEqual(val,30.)
        self.assertEqual(n,0)
        previous.append({"metric":"pass_attempts","state":"favored","error":15.})
        val,n=corrected(30,"favored","pass_attempts",previous)
        self.assertGreater(val,30)
        self.assertLessEqual(val,35)
        self.assertEqual(n,MIN_CORRECTION)
    def test_intervals_never_use_unseen_future(self):
        history=[{"metric":"rush_attempts","error":3.} for _ in range(MIN_INTERVAL)]
        self.assertIsNone(interval(25,"rush_attempts",history[:-1]))
        self.assertEqual(interval(25,"rush_attempts",history),(22.,28.))
        self.assertIsNone(interval(25,"pass_attempts",history))
    def test_pregame_strength_cannot_use_current_scores(self):
        _,schedule=fixture()
        before=pregame_state(schedule,"LA","BUF",{1})
        after=schedule.copy()
        after.loc[after.week==3,["home_score","away_score"]]=[99,0]
        self.assertEqual(before,pregame_state(after,"LA","BUF",{1}))
    def test_week_results_cannot_affect_own_week_predictions(self):
        history,schedule=fixture()
        out=evaluate(history,schedule,2,2)
        changed=history.copy()
        changed.loc[(changed.season==2026)&(changed.week==3)&
                    (changed.player_id=="qBUF"),"attempts"]=200
        self.assertEqual(out["accuracy"],evaluate(changed,schedule,2,2)["accuracy"])
    def test_result_remains_unpromoted_with_insufficient_evidence(self):
        history,schedule=fixture()
        result=evaluate(history,schedule,2,3)
        self.assertFalse(result["phase22_promoted"])
        self.assertEqual(result["production_champion"],"phase20")
        self.assertIn("Do NOT replace Phase 20",markdown(result))
        self.assertEqual(result["interval80_checks"][0]["n"],0)
    def test_incomplete_week_not_scored(self):
        history,schedule=fixture()
        schedule.loc[schedule.week==3,"home_score"]=float("nan")
        result=evaluate(history,schedule,2,3)
        self.assertEqual(result["tested_weeks"],[2])
if __name__=="__main__":unittest.main()
