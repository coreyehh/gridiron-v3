import unittest
import pandas as pd
from test_phase23_role_model import sample
from scripts.phase24_participation_calibration import (
  availability_gate,empirical_probability,evaluate,markdown,MIN_HISTORY)
class Phase24Tests(unittest.TestCase):
    def test_roster_does_not_verify_game_day_actives(self):
        gate=availability_gate([{"player_id":"p","team":"LA"}])
        self.assertFalse(gate["game_day_actives_verified"])
        self.assertFalse(gate["bet_eligible"])
    def test_lack_of_residuals_fails_probability(self):
        self.assertIsNone(empirical_probability([0]*49,3.,2.5))
    def test_probability_uses_only_frozen_prior_residuals(self):
        history=[0.]*MIN_HISTORY
        p=empirical_probability(history,3.,2.5)
        self.assertGreater(p,.9)
        self.assertLess(p,1.)
        self.assertEqual(len(history),MIN_HISTORY)
        self.assertNotEqual(p,empirical_probability(history+[100.],3.,2.5))
    def test_same_week_does_not_enter_training(self):
        h,s=sample()
        a=evaluate(h,s,4,4)
        new=h.copy()
        mask=(new.season==2026)&(new.week==4)&(new.player_id=="wrBUF")
        new.loc[mask,"receiving_yards"]=300.
        b=evaluate(new,s,4,4)
        self.assertEqual(a["player_game_evaluations"],b["player_game_evaluations"])
        self.assertEqual(a["probability_metrics"],b["probability_metrics"])
    def test_no_bookmaker_claims(self):
        h,s=sample()
        result=evaluate(h,s,4,4)
        self.assertFalse(result["bookmaker_prices_used"])
        self.assertFalse(result["availability"]["bet_eligible"])
        self.assertIn("NOT live sportsbook",markdown(result))
if __name__=="__main__":unittest.main()
