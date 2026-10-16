import unittest
import pandas as pd
from scripts.phase21_walkforward import evaluate,grading_environment,markdown
def fixture():
    rows=[]
    for year,weeks in ((2025,range(14,19)),(2026,range(1,4))):
        for wk in weeks:
            for team,att in (("BUF",18),("LA",40)):
                rows.extend([
                    {"season":year,"week":wk,"recent_team":team,"season_type":"REG",
                     "player_id":"q"+team,"position":"QB","attempts":att,"carries":3,
                     "targets":0,"receptions":0,"receiving_yards":0},
                    {"season":year,"week":wk,"recent_team":team,"season_type":"REG",
                     "player_id":"wr"+team,"position":"WR","attempts":0,"carries":0,
                     "targets":att//2,"receptions":att//3,"receiving_yards":att*3.0},
                    {"season":year,"week":wk,"recent_team":team,"season_type":"REG",
                     "player_id":"rb"+team,"position":"RB","attempts":0,"carries":14,
                     "targets":att//5,"receptions":att//6,"receiving_yards":att*0.75}])
    schedule=pd.DataFrame([{"season":2026,"week":w,"game_type":"REG",
             "home_team":"LA","away_team":"BUF","gameday":f"2026-09-{w+6:02d}",
             "home_score":37 if w==2 else 17,"away_score":34 if w==2 else 14}
             for w in (1,2,3)])
    return pd.DataFrame(rows),schedule
class WalkforwardTests(unittest.TestCase):
    def test_walkforward_excludes_target_week_feature_leakage(self):
        h,s=fixture()
        a=evaluate(h,s,2,3)
        mutated=h.copy()
        idx=(mutated.season==2026)&(mutated.week==3)&(mutated.player_id=="wrBUF")
        mutated.loc[idx,"receiving_yards"]=300
        b=evaluate(mutated,s,2,2)
        c=evaluate(h,s,2,2)
        self.assertEqual(b["team_accuracy"],c["team_accuracy"])
        self.assertEqual(b["player_accuracy"],c["player_accuracy"])
        self.assertEqual(a["tested_weeks"],[2,3])
    def test_scoring_environment_not_feature(self):
        h,s=fixture()
        a=evaluate(h,s,2,2)
        s2=s.copy()
        s2.loc[s2.week==2,"home_score"]=0
        s2.loc[s2.week==2,"away_score"]=0
        b=evaluate(h,s2,2,2)
        self.assertEqual(a["team_accuracy"],b["team_accuracy"])
        self.assertEqual(a["player_accuracy"],b["player_accuracy"])
        self.assertNotEqual(a["environment_slices"],b["environment_slices"])
    def test_future_incomplete_week_excluded(self):
        h,s=fixture()
        s.loc[s.week==3,"home_score"]=float("nan")
        out=evaluate(h,s,2,3)
        self.assertEqual(out["tested_weeks"],[2])
    def test_score_buckets_for_grading(self):
        _,s=fixture()
        self.assertEqual(grading_environment(s,2,"LA","BUF")["total_bucket"],"high_50plus")
    def test_readable_summary_and_no_betting_claim(self):
        h,s=fixture()
        out=evaluate(h,s,2,3)
        page=markdown(out)
        self.assertIn("Phase 20 MAE",page)
        self.assertIn("NOT betting probabilities",page)
        self.assertEqual(out["bets_qualified"],0)
if __name__=="__main__":unittest.main()
