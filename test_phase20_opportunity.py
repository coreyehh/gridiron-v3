import unittest
import pandas as pd
from scripts.phase20_opportunity import normalize,team_games,opportunity_forecast,player_forecast,markdown
def sample():
    rows=[]
    for season,weeks in ((2025,range(14,19)),(2026,range(1,5))):
        for w in weeks:
            for team,q,attempts in (("BUF","qbBUF",18),("LA","qbLA",40)):
                rows.extend([
                 {"season":season,"week":w,"player_id":q,"position":"QB","recent_team":team,
                  "attempts":attempts,"carries":3,"targets":0,"receptions":0,"receiving_yards":0},
                 {"season":season,"week":w,"player_id":"wr"+team,"position":"WR","recent_team":team,
                  "attempts":0,"carries":0,"targets":int(attempts*.5),"receptions":int(attempts*.3),"receiving_yards":int(attempts*3.5)},
                 {"season":season,"week":w,"player_id":"rb"+team,"position":"RB","recent_team":team,
                  "attempts":0,"carries":14,"targets":int(attempts*.2),"receptions":int(attempts*.15),"receiving_yards":int(attempts)},
                 ])
    return pd.DataFrame(rows)
def schedule():
    data=[]
    for wk in range(1,5):
        data.append({"season":2026,"week":wk,"game_type":"REG","home_team":"LA",
                     "away_team":"BUF","gameday":"2026-09-01","home_score":20,"away_score":28})
    return pd.DataFrame(data)
class OpportunityTests(unittest.TestCase):
    def test_points_do_not_force_pass_attempts(self):
        games=team_games(sample())
        p=opportunity_forecast(games,schedule(),"BUF","LA",{1,2,3,4})
        self.assertEqual(p["BUF"]["pass_attempts"]["projection"],18)
        self.assertEqual(p["LA"]["pass_attempts"]["projection"],40)
    def test_player_share_respects_team_volume(self):
        h=sample();g=team_games(h)
        p=opportunity_forecast(g,schedule(),"BUF","LA",{1,2,3,4})
        buf=player_forecast(h,p["BUF"],{1,2,3,4},"BUF")
        la=player_forecast(h,p["LA"],{1,2,3,4},"LA")
        self.assertLess(next(x for x in buf if x["player_id"]=="wrBUF")["targets_projection"],next(x for x in la if x["player_id"]=="wrLA")["targets_projection"])
    def test_post_target_rows_do_not_change_projection(self):
        a=sample()
        fake=pd.DataFrame([{"season":2026,"week":5,"player_id":"wrBUF","position":"WR",
          "recent_team":"BUF","attempts":0,"carries":0,"targets":100,"receptions":100,"receiving_yards":1000}])
        b=pd.concat([a,fake],ignore_index=True)
        g=team_games(a);p=opportunity_forecast(g,schedule(),"BUF","LA",{1,2,3,4})
        fa=player_forecast(a,p["BUF"],{1,2,3,4},"BUF")
        fb=player_forecast(b,p["BUF"],{1,2,3,4},"BUF")
        self.assertEqual(fa,fb)
    def test_missing_targets_fail_closed(self):
        with self.assertRaises(ValueError):
            team_games(sample().drop(columns=["targets"]))
    def test_no_completed_history_fails(self):
        with self.assertRaises(ValueError):
            opportunity_forecast(team_games(sample()),schedule(),"BUF","LA",set())
    def test_public_report_disclaims_bets(self):
        p=opportunity_forecast(team_games(sample()),schedule(),"BUF","LA",{1,2,3,4})
        doc={"matchup":"BUF vs LA","target_week":5,"team_projection":p,
             "player_projections":[]}
        text=markdown(doc)
        self.assertIn("NOT sportsbook picks",text)
if __name__=="__main__":unittest.main()
