import unittest
import pandas as pd
from scripts.opportunity import team_volume, build_opportunities, normalize_team_column

class OpportunityTests(unittest.TestCase):
    def test_team_volume_is_lagged(self):
        pbp=pd.DataFrame([
          {"season":2024,"week":1,"posteam":"CIN","pass_attempt":1,"season_type":"REG"},
          {"season":2024,"week":1,"posteam":"CIN","pass_attempt":1,"season_type":"REG"},
          {"season":2024,"week":2,"posteam":"CIN","pass_attempt":1,"season_type":"REG"},
          {"season":2024,"week":2,"posteam":"CIN","pass_attempt":1,"season_type":"POST"},
        ])
        team=team_volume(pbp)
        self.assertEqual(team.iloc[0].team_pass_attempts,2)
        self.assertEqual(team.iloc[1].team_pass_attempts,1)
        self.assertEqual(team.iloc[1].prior_team_pass_attempts_5,2)
    def test_current_game_targets_not_in_current_lag(self):
        rows=[]
        for week,targets in [(1,2),(2,20),(3,0)]:
            rows.append(dict(season=2024,week=week,player_id="P1",position="RB",
                recent_team="CIN",season_type="REG",targets=targets,
                receptions=1,receiving_yards=10))
        volume=pd.DataFrame([dict(season=2024,week=w,team="CIN",team_pass_attempts=40,
                                  prior_team_pass_attempts_5=40) for w in (1,2,3)])
        base=pd.DataFrame([dict(season=2024,week=w,player_id="P1",prior_position="RB") for w in (1,2,3)])
        combined,_=build_opportunities(pd.DataFrame(rows),base,volume)
        self.assertEqual(combined.iloc[1].prior_rb_targets_5,2)
        self.assertEqual(combined.iloc[2].prior_rb_targets_5,11)
        self.assertAlmostEqual(combined.iloc[1].prior_rb_target_share_5,0.05)
    def test_official_team_column_supported(self):
        x=normalize_team_column(pd.DataFrame({"team":["CIN"],"player_id":["P1"]}))
        self.assertEqual(x.observed_team.iloc[0],"CIN")
    def test_conflicting_team_fields_fail(self):
        with self.assertRaises(ValueError):
            normalize_team_column(pd.DataFrame({"team":["CIN"],"recent_team":["BAL"]}))
    def test_missing_columns_rejected(self):
        with self.assertRaises(ValueError):
            build_opportunities(pd.DataFrame({"season":[2025]}),pd.DataFrame(),pd.DataFrame())

if __name__=="__main__":
    unittest.main()
