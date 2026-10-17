import unittest
from datetime import datetime,timezone
import pandas as pd
from test_phase23_role_model import sample
from scripts.phase26_matchup_board import pick_game,build,markdown,historical_residuals
from scripts.phase20_opportunity import normalize,team_games

def prep():
    history,schedule=sample()
    schedule.loc[schedule.week==4,["home_score","away_score"]]=float("nan")
    roster=[{"team":team,"player_id":pid,"player_name":name}
     for team in ("LA","BUF") for pid,name in [
        ("wr"+team,"Receiver "+team),("rb"+team,"Runner "+team)]]
    clock=datetime(2026,9,9,12,0,tzinfo=timezone.utc)
    return history,schedule,roster,clock

class Phase26Tests(unittest.TestCase):
    def test_auto_selects_first_strictly_future_game(self):
        h,s,r,t=prep()
        match=pick_game(s,asof=t)
        self.assertEqual(match["week"],4)
        self.assertEqual(match["home"],"LA")
    def test_requires_two_matched_teams(self):
        _,s,_,t=prep()
        with self.assertRaises(ValueError):pick_game(s,team_a="BUF",week=4,asof=t)
        with self.assertRaises(ValueError):pick_game(s,"BUF","DEN",4,t)
    def test_rejects_completed_matchup(self):
        _,s,_,t=prep()
        s.loc[s.week==4,["home_score","away_score"]]=[21,14]
        with self.assertRaises(ValueError):pick_game(s,"LA","BUF",4,t)
    def test_end_to_end_team_and_player_research(self):
        h,s,r,t=prep()
        report=build(s,h,r,"LA","BUF",4,t)
        self.assertEqual(report["qualified_bets"],0)
        self.assertEqual(report["game"]["week"],4)
        self.assertTrue(report["player_forecasts"])
        self.assertFalse(report["game_day_actives_verified"])
        self.assertFalse(report["calibrated_real_line_probabilities"])
        self.assertIn("Receiving yards",markdown(report))
        self.assertEqual(report["historical_probability_training_weeks"],[])
    def test_same_week_stat_changes_do_not_affect_forecasts(self):
        h,s,r,t=prep()
        a=build(s,h,r,"LA","BUF",4,t)
        edited=h.copy()
        edited.loc[(edited.season==2026)&(edited.week==4)&
          (edited.player_id=="wrBUF"),"receiving_yards"]=500
        b=build(s,edited,r,"LA","BUF",4,t)
        self.assertEqual(a["team_projection"],b["team_projection"])
        self.assertEqual(a["player_forecasts"],b["player_forecasts"])
    def test_unverified_player_never_becomes_pick(self):
        h,s,r,t=prep()
        x=build(s,h,r,"LA","BUF",4,t)
        self.assertTrue(all(p["bet_status"]=="RESEARCH_ONLY" for p in x["player_forecasts"]))
        self.assertTrue(all(not p["game_day_active_confirmed"] for p in x["player_forecasts"]))
    def test_previous_residuals_exclude_target_week(self):
        h,s,r,t=prep()
        games=team_games(normalize(h))
        hist,trained=historical_residuals(normalize(h),games,s,4,{1,2,3})
        self.assertEqual(trained,[])
        self.assertEqual(dict(hist),{})
if __name__=="__main__":unittest.main()
