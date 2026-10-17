import unittest,tempfile,json
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from scripts.phase31_accountability import (
 build_snapshot,verify_snapshot,grade_snapshot,audit,choose_week,MODEL)
from test_phase26_matchup_board import prep

def fixture():
    h,s,r,old=prep()
    now=datetime(2026,9,9,12,tzinfo=timezone.utc)
    s.loc[s.week==4,"gameday"]="2026-09-10"
    s.loc[s.week==4,["home_score","away_score"]]=float("nan")
    return h,s,r,now

class Phase31Tests(unittest.TestCase):
    def test_future_week_selection(self):
        h,s,r,now=fixture()
        self.assertEqual(choose_week(s,now),4)
    def test_snapshot_locked_and_safely_hashed(self):
        h,s,r,now=fixture()
        snap=build_snapshot(s,h,r,now,4,{"synthetic":"hash"})
        self.assertTrue(verify_snapshot(snap))
        self.assertEqual(snap["week"],4)
        self.assertTrue(snap["forecasts"])
        self.assertFalse(snap["official_actives_verified"])
    def test_hash_detects_rewritten_forecast(self):
        h,s,r,now=fixture()
        snap=build_snapshot(s,h,r,now,4,{})
        snap["forecasts"][0]["receiving_yards"]=9999.
        with self.assertRaisesRegex(ValueError,"hash mismatch"):
            verify_snapshot(snap)
    def test_cannot_capture_same_day_fixture(self):
        h,s,r,now=fixture()
        s.loc[s.week==4,"gameday"]="2026-09-09"
        with self.assertRaises(ValueError):build_snapshot(s,h,r,now,4,{})
    def test_does_not_use_current_week_targets(self):
        h,s,r,now=fixture()
        original=build_snapshot(s,h,r,now,4,{})
        mutated=h.copy()
        mutated.loc[(mutated.season==2026)&(mutated.week==4),"targets"]=999.
        new=build_snapshot(s,mutated,r,now,4,{})
        self.assertEqual(original["forecasts"],new["forecasts"])
    def test_unplayed_week_is_not_scored(self):
        h,s,r,now=fixture()
        snap=build_snapshot(s,h,r,now,4,{})
        grade=grade_snapshot(snap,s,h,now)
        self.assertEqual(grade["status"],"waiting_for_completed_week")
    def test_missing_player_not_an_inactive_or_loss(self):
        h,s,r,now=fixture()
        snap=build_snapshot(s,h,r,now,4,{})
        s.loc[s.week==4,["home_score","away_score"]]=[20.,17.]
        future=datetime(2026,9,11,12,tzinfo=timezone.utc)
        # Drop target-week rows so every forecasted player is unresolved.
        none=h[~((h.season==2026)&(h.week==4))].copy()
        grade=grade_snapshot(snap,s,none,future)
        self.assertEqual(grade["graded"],0)
        self.assertEqual(grade["unknown_participation"],len(snap["forecasts"]))
        self.assertEqual(grade["status"],"graded_participation_unknown_excluded")
    def test_idempotent_immutable_snapshot(self):
        h,s,r,now=fixture()
        with tempfile.TemporaryDirectory() as temp:
            first=audit(temp,s,h,r,now,{})
            self.assertIsNotNone(first["snapshot_created"])
            path=next(Path(temp).glob("2026-week-*.json"))
            content=path.read_bytes()
            second=audit(temp,s,h,r,now,{})
            self.assertIsNone(second["snapshot_created"])
            self.assertEqual(second["snapshot_skipped_reason"],
                             "immutable_week_snapshot_already_exists")
            self.assertEqual(path.read_bytes(),content)
    def test_tampered_file_fails_closed(self):
        h,s,r,now=fixture()
        with tempfile.TemporaryDirectory() as temp:
            audit(temp,s,h,r,now,{})
            path=next(Path(temp).glob("2026-week-*.json"))
            d=json.loads(path.read_text());d["forecasts"][0]["targets"]=101.
            path.write_text(json.dumps(d))
            with self.assertRaisesRegex(ValueError,"hash mismatch"):audit(temp,s,h,r,now,{})
if __name__=="__main__":unittest.main()
