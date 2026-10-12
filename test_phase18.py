import unittest
import pandas as pd
from scripts.phase18 import target_game,completed_weeks,frozen_features,compare,forecast_prequote
from test_phase17 import history
from scripts.phase17 import FEATURES
from scripts.ingest import MEASURES

T="2026-10-12T20:00:00Z"
E={"id":"event","commence_time":"2026-10-19T00:20:00Z",
   "home_team":"Cincinnati Bengals","away_team":"Baltimore Ravens"}
def schedule():
 return pd.DataFrame([
  {"season":2026,"week":5,"game_type":"REG","home_team":"CIN","away_team":"BAL","gameday":"2026-10-11","home_score":25,"away_score":17},
  {"season":2026,"week":5,"game_type":"REG","home_team":"KC","away_team":"DEN","gameday":"2026-10-11","home_score":31,"away_score":20},
  {"season":2026,"week":6,"game_type":"REG","home_team":"CIN","away_team":"BAL","gameday":"2026-10-18","home_score":None,"away_score":None}
 ])
class Phase18Tests(unittest.TestCase):
 def test_primetime_utc_day(self):
  self.assertEqual(target_game(schedule(),2026,"CIN","BAL",E["commence_time"],T),6)
 def test_incomplete_previous_week_cannot_enter(self):
  d=schedule()
  # Remove week 1-4 from fixture, so even week 5 final is not treated as complete.
  self.assertEqual(completed_weeks(d,6,T),set())
  d=pd.DataFrame([{"season":2026,"week":1,"game_type":"REG","home_team":"CIN",
   "away_team":"BAL","gameday":"2026-09-10","home_score":1,"away_score":2},
   {"season":2026,"week":1,"game_type":"REG","home_team":"KC",
   "away_team":"DEN","gameday":"2026-09-10","home_score":None,"away_score":None}])
  self.assertEqual(completed_weeks(d,2,T),set())
 def test_latest_2026_stats_used_if_week_completed(self):
  h=history()
  h=pd.concat([h,pd.DataFrame([{"player_id":"id1","season":2026,"week":1,
   "position":"WR","receptions":10.,"receiving_yards":120.,
   "rushing_yards":0.,"passing_yards":0.}])],ignore_index=True)
  f=frozen_features(h)
  self.assertEqual(f["id1"]["observed_2026"],1)
  self.assertEqual(f["id1"]["last_season"],2026)
 def test_lock_checks_market_provider_timestamp(self):
  q={"event_id":"event","season":2026,"kickoff_utc":"2026-10-19T00:20:00Z",
     "home_team":"Cincinnati Bengals","away_team":"Baltimore Ravens",
     "player_display_name":"Synthetic Person","market":"receptions",
     "quoted_at_utc":"2026-10-12T20:01:00Z","captured_at_utc":"2026-10-12T20:02:00Z","line":3.5}
  lock={"locked_at_utc":"2026-10-12T20:01:30Z","sha256":"test"}
  out=compare([], [q],[], lock)
  self.assertEqual(out["quoted_before_lock_excluded"],1)
  with self.assertRaises(ValueError):
   compare([],[{**q,"captured_at_utc":"2026-10-12T20:01:00Z"}],[],lock)
 def test_forecast_fails_on_unmapped_schedule(self):
  with self.assertRaises(ValueError):
   forecast_prequote([],history(),schedule(),{**E,"home_team":"Fake Team"}, {},T)
if __name__=="__main__":unittest.main()
