import unittest
import pandas as pd
from scripts.participation import split_offense_ids, on_field_pass_snaps, make_features

class ParticipationTests(unittest.TestCase):
    def test_gsis_list(self):
        self.assertEqual(split_offense_ids("00-0031234;00-0035678"),
                         ["00-0031234","00-0035678"])
    def test_bad_identifiers_fail(self):
        with self.assertRaises(ValueError):
            split_offense_ids("unknown")
    def test_current_week_not_in_current_pregame_feature(self):
        p=pd.DataFrame([{"game_id":"2024_01_BAL_KC","play_id":1,"season":2024,"week":1,
                         "posteam":"KC","pass_attempt":1,"season_type":"REG"},
                        {"game_id":"2024_02_KC_CIN","play_id":1,"season":2024,"week":2,
                         "posteam":"KC","pass_attempt":1,"season_type":"REG"}])
        f=pd.DataFrame([{"nflverse_game_id":"2024_01_BAL_KC","play_id":1,
                         "offense_players":"00-0031234"},
                        {"nflverse_game_id":"2024_02_KC_CIN","play_id":1,
                         "offense_players":"00-0031234"}])
        counts,_=on_field_pass_snaps(p,f,{"00-0031234"},2024)
        w=pd.DataFrame([{"season":2024,"week":1,"player_id":"00-0031234",
                         "targets":1,"season_type":"REG"},
                        {"season":2024,"week":2,"player_id":"00-0031234",
                         "targets":10,"season_type":"REG"}])
        b=w[["season","week","player_id"]]
        result=make_features(b,w,counts)
        self.assertTrue(pd.isna(result.iloc[0].prior_rb_pass_play_snaps_5))
        self.assertEqual(result.iloc[1].prior_rb_pass_play_snaps_5,1)
        self.assertEqual(result.iloc[1].prior_rb_targets_per_pass_play_snap_5,1)
    def test_missing_participation_rejected(self):
        p=pd.DataFrame([{"game_id":"2024_01_BAL_KC","play_id":1,"season":2024,"week":1,
                         "posteam":"KC","pass_attempt":1,"season_type":"REG"}])
        f=pd.DataFrame(columns=["nflverse_game_id","play_id","offense_players"])
        with self.assertRaises(ValueError):
            on_field_pass_snaps(p,f,{"00-0031234"},2024)

if __name__=="__main__":unittest.main()
