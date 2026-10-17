import unittest
import pandas as pd
from scripts.phase28_snap_participation import (
 name_key,validate_snap_frame,conservative_join,prior_snap_factor,SNAP_URL)
from test_phase26_matchup_board import prep

def snaps():
    return pd.DataFrame([
      {"season":2026,"week":w,"game_type":"REG","team":"BUF","player":"Receiver BUF",
        "offense_snaps":v,"offense_pct":pct,"pfr_player_id":"PFR1"}
      for w,v,pct in [(1,50,.8),(2,51,.8),(3,20,.3),(4,60,.9)]])
class Phase28Tests(unittest.TestCase):
    def test_documented_real_source(self):
        self.assertIn("snap_counts/snap_counts_2026.parquet",SNAP_URL.format(season=2026))
    def test_name_key(self):
        self.assertEqual(name_key("José Receiver Jr."),"jose receiver")
    def test_rejects_duplicate_ambiguous_snap_names(self):
        with self.assertRaises(ValueError):
            validate_snap_frame(pd.concat([snaps(),snaps().iloc[[0]]]),2026)
    def test_fraction_and_percent_equivalent(self):
        v=snaps()
        p=v.copy();p["offense_pct"]*=100.
        a=validate_snap_frame(v,2026)
        b=validate_snap_frame(p,2026)
        self.assertEqual(a.offense_pct.round(3).tolist(),b.offense_pct.round(3).tolist())
    def test_prior_only_matching_and_shift(self):
        history,s,roster,now=prep()
        snap=validate_snap_frame(snaps(),2026)
        joined=conservative_join(history,snap,roster)
        f,n,diagnostic=prior_snap_factor(joined,"BUF","wrBUF",{1,2,3})
        self.assertEqual(n,3)
        self.assertLess(f,1.)
        modified=snap.copy()
        modified.loc[modified.week==4,"offense_pct"]=0.
        joined2=conservative_join(history,modified,roster)
        f2,_,_=prior_snap_factor(joined2,"BUF","wrBUF",{1,2,3})
        self.assertAlmostEqual(f,f2)
    def test_unmatched_names_do_not_get_snap_zero(self):
        history,s,roster,now=prep()
        joined=conservative_join(history,validate_snap_frame(snaps(),2026),roster)
        factor,n,details=prior_snap_factor(joined,"LA","wrLA",{1,2,3})
        self.assertEqual(factor,1.)
        self.assertEqual(n,0)
        self.assertIsNone(details)
    def test_only_one_prior_game_no_adjustment(self):
        history,s,roster,now=prep()
        joined=conservative_join(history,validate_snap_frame(snaps(),2026),roster)
        factor,n,_=prior_snap_factor(joined,"BUF","wrBUF",{1})
        self.assertEqual(n,1)
        self.assertEqual(factor,1.)
if __name__=="__main__":unittest.main()
