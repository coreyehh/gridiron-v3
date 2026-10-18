import unittest,copy
from datetime import datetime,timezone
import pandas as pd
from scripts.phase43_remaining_week6 import verified_kickoff,future_fixtures,build_remaining,check_remaining
from test_phase43_multimarket_forecasts import history

def schedule():
    out=[]
    for week in range(1,6):
        out.append({"season":2026,"week":week,"game_type":"REG",
          "home_team":"ATL","away_team":"CHI",
          "gameday":f"2026-09-{week+5:02d}","gametime":"13:00",
          "home_score":24.0,"away_score":10.0})
    for home,away,day,clock,score in [
        ("ATL","CHI","2026-10-18","13:00",None),
        ("NYG","NO","2026-10-18","16:25",None),
        ("SF","WAS","2026-10-19","20:15",None),
        ("HOU","JAX","2026-10-15","20:15",21.0)]:
        out.append({"season":2026,"week":6,"game_type":"REG",
          "home_team":home,"away_team":away,"gameday":day,
          "gametime":clock,"home_score":score,
          "away_score":14.0 if score is not None else None})
    return pd.DataFrame(out)

class RemainingWeek6Tests(unittest.TestCase):
    def test_kickoff_utc_uses_eastern_dst(self):
        game={"gameday":"2026-10-18","gametime":"13:00"}
        self.assertEqual(verified_kickoff(game).isoformat(),"2026-10-18T17:00:00+00:00")
    def test_same_day_unstarted_is_included(self):
        matches,rejected=future_fixtures(schedule(),6,
                    datetime(2026,10,18,16,0,tzinfo=timezone.utc))
        self.assertEqual(len(matches),3)
        self.assertEqual(len(rejected),1)
    def test_after_one_pm_excludes_that_kickoff_but_keeps_later(self):
        matches,_=future_fixtures(schedule(),6,
                    datetime(2026,10,18,17,1,tzinfo=timezone.utc))
        self.assertEqual({x["id"] for x in matches},
            {"2026-W06-NO-at-NYG","2026-W06-WAS-at-SF"})
    def test_earlier_scored_game_excluded(self):
        matches,excluded=future_fixtures(schedule(),6,
                    datetime(2026,10,18,16,0,tzinfo=timezone.utc))
        self.assertEqual(len([e for e in excluded if e["reason"]=="ALREADY_SCORED_OR_SCORE_PARTIAL"]),1)
    def test_fail_closed_without_game_time(self):
        with self.assertRaises(ValueError):
            future_fixtures(schedule().drop(columns="gametime"),6,
                 datetime(2026,10,18,16,0,tzinfo=timezone.utc))
    def test_full_future_snapshot_has_only_unstarted_games(self):
        roster=[{"team":"ATL","player_id":"p1","player_name":"Synthetic QB","position":"QB"}]
        snap,meta=build_remaining(schedule(),history(),roster,
                 datetime(2026,10,18,16,0,tzinfo=timezone.utc),{"synthetic":"yes"})
        self.assertEqual(meta["fixtures"],3)
        self.assertTrue(check_remaining(snap))
        self.assertTrue(all(f["kickoff_utc"]>"2026-10-18T16:00:00" for f in snap["fixtures"]))
        self.assertEqual(snap["qualified_bets"],0)
        self.assertFalse(snap["touchdown_probabilities_calibrated"])
    def test_future_data_leakage_never_reaches_prediction(self):
        roster=[{"team":"ATL","player_id":"p1","player_name":"Synthetic QB","position":"QB"}]
        snap,_=build_remaining(schedule(),history(),roster,
                 datetime(2026,10,18,16,0,tzinfo=timezone.utc),{})
        # The synthetic 2026 week 6 row and future week 7 outlier must not enter training.
        self.assertLess(snap["forecasts"][0]["point_projections"]["passing_yards"],300)
    def test_snapshot_hash_mismatch_rejected(self):
        roster=[{"team":"ATL","player_id":"p1","player_name":"Synthetic QB","position":"QB"}]
        snap,_=build_remaining(schedule(),history(),roster,
                 datetime(2026,10,18,16,0,tzinfo=timezone.utc),{})
        snap["forecasts"][0]["point_projections"]["rushing_yards"]=9000
        with self.assertRaises(ValueError):check_remaining(snap)
    def test_after_all_kickoffs_returns_no_backfill(self):
        snap,report=build_remaining(schedule(),history(),[],
                datetime(2026,10,20,0,30,tzinfo=timezone.utc),{})
        self.assertIsNone(snap)
        self.assertEqual(report["status"],"NO_UNSTARTED_WEEK6_FIXTURES")
if __name__=="__main__":unittest.main()
