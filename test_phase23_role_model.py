import unittest
import pandas as pd
from test_phase21_walkforward import fixture
from scripts.phase23_role_model import role_forecast,backtest,markdown

def sample():
    h,s=fixture()
    # Minimum prior team games for week 4 evaluation. Complete week 4.
    future=s.iloc[-1].copy()
    future["week"]=4
    future["home_score"]=24
    future["away_score"]=14
    s=pd.concat([s,pd.DataFrame([future])],ignore_index=True)
    f=h[h.week.eq(3)&h.season.eq(2026)].copy()
    f["week"]=4
    h=pd.concat([h,f],ignore_index=True)
    return h,s

class RoleTests(unittest.TestCase):
    def test_fails_closed_on_insufficient_form(self):
        h,_=sample()
        self.assertEqual(role_forecast(h,30,{1,2},"BUF"),[])
    def test_player_role_target_share_is_bounded_by_real_history(self):
        h,_=sample()
        out=role_forecast(h,30,{1,2,3},"BUF")
        wr=next(x for x in out if x["player_id"]=="wrBUF")
        self.assertGreater(wr["targets"],1)
        self.assertLess(wr["targets"],30)
        self.assertFalse(wr["availability_verified"])
    def test_target_week_leakage_is_excluded(self):
        h,_=sample()
        prior=role_forecast(h,30,{1,2,3},"BUF")
        tampered=h.copy()
        mask=(tampered.season==2026)&(tampered.week==4)&(tampered.player_id=="wrBUF")
        tampered.loc[mask,"targets"]=900
        self.assertEqual(prior,role_forecast(tampered,30,{1,2,3},"BUF"))
    def test_walkforward_reports_same_cohort(self):
        h,s=sample()
        result=backtest(h,s,4,4)
        self.assertEqual(result["weeks"],[4])
        self.assertEqual(result["rows"],result["player_games"]*3)
        self.assertEqual([x["observations"] for x in result["metrics"]],[result["player_games"]]*3)
        self.assertIn("Player role accuracy audit",markdown(result))
    def test_future_outcomes_cannot_change_week4_error(self):
        h,s=sample()
        a=backtest(h,s,4,4)
        h2=h.copy()
        h2.loc[(h2.season==2026)&(h2.week==4)&(h2.player_id=="wrBUF"),"receiving_yards"]=300
        b=backtest(h2,s,4,4)
        # Outcomes change *accuracy*, not the historical model's features.
        self.assertEqual(a["player_games"],b["player_games"])
        self.assertNotEqual(a["metrics"],b["metrics"])
if __name__=="__main__":unittest.main()
