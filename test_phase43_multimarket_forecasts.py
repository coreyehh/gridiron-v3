import unittest,copy
from datetime import datetime,timezone
import pandas as pd
from scripts.phase43_multimarket_forecasts import (
 prep,tails,forecast_player,build,verify,walk_forward)
def history():
    rows=[]
    for yr,weeks in [(2025,range(14,19)),(2026,range(1,7))]:
        for wk in weeks:
            rows.append({"season":yr,"week":wk,"season_type":"REG",
            "player_id":"p1","recent_team":"ATL","position":"QB",
            "passing_yards":200+wk,"attempts":30,"completions":20,
            "interceptions":0,"passing_tds":2,"rushing_yards":10,
            "carries":3,"rushing_tds":0,"receiving_tds":0})
    # Explicit target week 7 future result leakage bait — must be excluded
    rows.append({**rows[-1],"week":7,"passing_yards":5000,"passing_tds":99})
    return pd.DataFrame(rows)
def schedule():
    r=[]
    for wk in range(1,8):
        r.append({"season":2026,"week":wk,"game_type":"REG",
          "home_team":"ATL","away_team":"CHI",
          "gameday":f"2026-10-{10+wk:02d}",
          "home_score":None if wk==7 else 20,
          "away_score":None if wk==7 else 13})
    return pd.DataFrame(r)
class Phase43Tests(unittest.TestCase):
    def test_poisson_probabilities_monotone(self):
        t=tails(0.9)
        self.assertGreater(t["anytime_touchdown"],t["two_plus_touchdowns"])
        self.assertGreater(t["two_plus_touchdowns"],t["three_plus_touchdowns"])
        self.assertTrue(all(0<=p<=1 for p in t.values()))
    def test_zero_touchdowns_no_invented_scores(self):
        self.assertEqual(tails(0)["three_plus_touchdowns"],0)
        self.assertEqual(tails(0)["anytime_touchdown"],0)
    def test_no_negative_td_rate(self):
        with self.assertRaises(ValueError):tails(-1)
    def test_stat_schema_fail_closed(self):
        with self.assertRaises(ValueError):prep(history().drop(columns="passing_tds"))
    def test_player_baselines_source_and_no_fake_edge(self):
        f=forecast_player(prep(history().query("week != 7")),"QB")
        self.assertIsNotNone(f["point_projections"]["passing_yards"])
        self.assertAlmostEqual(f["point_projections"]["passing_touchdowns"],2,places=3)
        self.assertFalse(f["qualified_bet"])
        self.assertFalse(f["active_verified"])
    def test_week7_target_data_cannot_leak_into_future_projection(self):
        rows=history()
        obj=build(schedule(),rows,
          [{"team":"ATL","player_id":"p1","player_name":"Test Quarterback","position":"QB"}],
          7,datetime(2026,10,16,tzinfo=timezone.utc),{"synthetic":"yes"})
        self.assertTrue(verify(obj))
        self.assertEqual(len(obj["forecasts"]),1)
        self.assertLess(obj["forecasts"][0]["point_projections"]["passing_yards"],300)
        self.assertNotIn("5000",str(obj))
        self.assertEqual(obj["qualified_bets"],0)
    def test_nonfuture_snapshots_cannot_be_forged(self):
        rows=history()
        with self.assertRaises(ValueError):
            build(schedule(),rows,[{"team":"ATL","player_id":"p1",
                    "player_name":"Test QB","position":"QB"}],
               7,datetime(2026,10,20,tzinfo=timezone.utc),{})
    def test_incomplete_prior_week_must_block(self):
        s=schedule();s.loc[s.week==6,"home_score"]=None
        with self.assertRaises(ValueError):
            build(s,history(),[],7,datetime(2026,10,16,tzinfo=timezone.utc),{})
    def test_immutable_hash_rejects_mutation(self):
        obj=build(schedule(),history(),
           [{"team":"ATL","player_id":"p1","player_name":"Test QB","position":"QB"}],
           7,datetime(2026,10,16,tzinfo=timezone.utc),{})
        obj["forecasts"][0]["point_projections"]["rushing_yards"]=99999
        with self.assertRaises(ValueError):verify(obj)
    def test_walk_forward_missing_player_rows_not_imputed(self):
        x=walk_forward(history(),4,6)
        self.assertTrue(x["absent_box_rows_not_imputed"])
        self.assertGreater(x["scored_rows"],0)
        self.assertFalse(x["td_probability_calibration"])
    def test_unobserved_player_no_projection(self):
        self.assertIsNone(forecast_player(prep(history()).head(2),"QB"))
    def test_2026_future_rows_ignored_in_training(self):
        obj=build(schedule(),history(),
           [{"team":"ATL","player_id":"p1","player_name":"Test QB","position":"QB"}],
           7,datetime(2026,10,16,tzinfo=timezone.utc),{})
        self.assertEqual(obj["prior_completed_weeks"],[1,2,3,4,5,6])
        self.assertFalse(obj["uses_bookmaker_odds"])
        self.assertFalse(obj["td_2plus_3plus_probabilities_validated"])
if __name__=="__main__":unittest.main()
