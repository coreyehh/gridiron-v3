import unittest
from datetime import datetime,timezone
import pandas as pd
from test_phase26_matchup_board import prep
from scripts.phase27_matchup_context import (
    position_multiplier,rest_days,augment,backtest,markdown,opponent_history)
from scripts.phase26_matchup_board import build

class Phase27Tests(unittest.TestCase):
    def test_no_current_week_position_leakage(self):
        stats,s,_,_=prep()
        from scripts.phase20_opportunity import normalize
        history=normalize(stats)
        old=opponent_history(history,s,"LA",{1,2,3},"WR")
        changed=history.copy()
        changed.loc[(changed.season==2026)&(changed.week==4)&
            (changed.player_id=="wrBUF"),"targets"]=999
        self.assertEqual(old,opponent_history(changed,s,"LA",{1,2,3},"WR"))
    def test_no_multiplier_without_three_prior_games(self):
        from scripts.phase20_opportunity import normalize
        h,s,_,_=prep()
        factor,n,rate=position_multiplier(normalize(h),s,"LA",{1,2},"WR")
        self.assertEqual(factor,1.)
        self.assertLess(n,3)
    def test_multiplier_clamped(self):
        from scripts.phase20_opportunity import normalize
        h,s,_,_=prep()
        factor,n,rate=position_multiplier(normalize(h),s,"LA",{1,2,3},"WR")
        self.assertTrue(.95<=factor<=1.05)
        self.assertGreaterEqual(n,3)
    def test_rest_is_schedule_only(self):
        _,s,_,_=prep()
        self.assertEqual(rest_days(s,"BUF",4),7)
    def test_end_to_end_context_keeps_base_forecasts(self):
        h,s,r,t=prep()
        base=build(s,h,r,"LA","BUF",4,t)
        prior_values=[(x["player_id"],x["targets"],x["receiving_yards"]) for x in base["player_forecasts"]]
        board=augment(base,h,s,{1,2,3})
        self.assertEqual(board["qualified_bets"],0)
        self.assertFalse(board["context"]["official_injuries_verified"])
        self.assertEqual(prior_values,[(x["player_id"],x["targets"],x["receiving_yards"]) for x in board["player_forecasts"]])
        self.assertIn("Opponent target rates",markdown(board))
    def test_backtest_scored_realization_does_not_change_previous_features(self):
        h,s,_,_=prep()
        s.loc[s.week==4,["home_score","away_score"]]=[14,10]
        result=backtest(h,s,4,4)
        self.assertEqual(result["scored_weeks"],[4])
        self.assertFalse(result["promotion_to_production"])
        self.assertEqual(result["player_games"],result["metrics"][0]["n"])
if __name__=="__main__":unittest.main()
