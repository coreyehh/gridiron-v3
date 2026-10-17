import unittest
from unittest.mock import patch
import pandas as pd
from test_phase26_matchup_board import prep
from scripts.phase20_opportunity import normalize
from scripts.phase28_snap_participation import conservative_join,validate_snap_frame
from scripts.phase29_route_readiness import (
    density_factor,probe_route_participation,report_board,PARTICIPATION_URL)
def fixture():
    history,schedule,roster,asof=prep()
    snap=pd.DataFrame([{"season":2026,"week":w,"team":"BUF","player":"Receiver BUF",
       "game_type":"REG","offense_snaps":n,"offense_pct":.7}
        for w,n in [(1,40),(2,50),(3,30),(4,50)]])
    join=conservative_join(history,validate_snap_frame(snap,2026),roster)
    return history,schedule,roster,asof,join
class Phase29Tests(unittest.TestCase):
    def test_public_participation_source_requires_check(self):
        self.assertIn("pbp_participation_2026.parquet",PARTICIPATION_URL)
    def test_offline_probe_unavailable_stays_unverified(self):
        from urllib.error import HTTPError
        with patch("urllib.request.urlopen",side_effect=HTTPError("test",404,"not found",{},None)):
            result=probe_route_participation()
        self.assertFalse(result["download_available"])
        self.assertFalse(result["route_counts_derived"])
    def test_density_never_called_targets_per_route(self):
        h,s,r,t,joined=fixture()
        f,n,diag=density_factor(normalize(h),joined,"BUF","wrBUF",{1,2,3})
        self.assertEqual(n,3)
        self.assertTrue(.95<=f<=1.05)
        self.assertTrue(diag["actual_routes_run_unknown"])
    def test_current_week_stats_and_snaps_are_not_predictive(self):
        h,s,r,t,joined=fixture()
        f,n,_=density_factor(normalize(h),joined,"BUF","wrBUF",{1,2,3})
        altered=h.copy()
        mask=(altered.season==2026)&(altered.week==4)&(altered.player_id=="wrBUF")
        altered.loc[mask,"targets"]=80.
        altered_join=joined.copy()
        altered_join.loc[altered_join.week==4,"offense_snaps"]=1000.
        f2,n2,_=density_factor(normalize(altered),altered_join,"BUF","wrBUF",{1,2,3})
        self.assertEqual(n,n2)
        self.assertEqual(f,f2)
    def test_missing_snap_neutral(self):
        h,s,r,t,joined=fixture()
        f,n,d=density_factor(normalize(h),joined,"LA","wrLA",{1,2,3})
        self.assertEqual(f,1.)
        self.assertEqual(n,0)
        self.assertIsNone(d)
    def test_integrated_board_research_only(self):
        h,s,r,t,joined=fixture()
        # use deterministic future-date fixture from Phase26 tests
        with patch("scripts.phase29_route_readiness.board26") as fake:
            fake.return_value={"game":{"home":"LA","away":"BUF","week":4,"gameday":"2026-09-10"},
              "completed_weeks":[1,2,3],"player_forecasts":[{"player_id":"wrBUF",
              "team":"BUF","receiving_yards":40.}]}
            result=report_board(h,s,r,joined,"LA","BUF",4)
        self.assertEqual(result["qualified_bets"],0)
        self.assertFalse(result["player_forecasts"][0]["true_routes_run_known"])
        self.assertFalse(result["phase29_promoted"])
if __name__=="__main__":unittest.main()
