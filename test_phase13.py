import unittest
import numpy as np
import pandas as pd
from scripts.phase13 import shift_probability,tail_probability,thresholds,reliability,calibrate_group
from scripts.evaluate_eligible import FEATURES

class Phase13Tests(unittest.TestCase):
    def test_logit_shift(self):
        p=np.array([.01,.2,.5,.8,.99])
        self.assertTrue(np.allclose(p,shift_probability(p,0)))
        self.assertTrue(np.all(shift_probability(p,-.2)<p))
        self.assertTrue(np.all(np.diff(shift_probability(p,-.2))>0))
    def test_invalid_probabilities(self):
        for x in (0,1,-.2,float("nan")):
            with self.assertRaises(ValueError):shift_probability([x],.1)
    def test_duplicate_half_catch_thresholds_removed(self):
        self.assertEqual(thresholds(np.array([2.1]*50+[2.2]*50+[2.9]*50),"receptions"),[2.5])
    def test_residuals_minimum(self):
        with self.assertRaises(ValueError):tail_probability(3,3.5,[1]*49)
    def test_reliability_bins(self):
        e,b=reliability([0,1,1,0],[.1,.3,.6,.9])
        self.assertEqual(sum(x["n"] for x in b),4)
    def test_no_2025_tuning_leakage(self):
        rng=np.random.default_rng(7)
        def frame(n,year):
            d={k:rng.normal(size=n) for k in FEATURES}
            d.update(season=[year]*n,week=np.tile(np.arange(1,19),n//18+1)[:n],receptions=rng.poisson(3,size=n))
            return pd.DataFrame(d)
        tr=frame(360,2023);va=frame(360,2024);te=frame(360,2025)
        a=calibrate_group(tr,va,te,"receptions")
        te["receptions"]=1000
        b=calibrate_group(tr,va,te,"receptions")
        self.assertEqual(a["selected_offset_on_2024"],b["selected_offset_on_2024"])
        self.assertEqual(a["locked_shrunk_offset"],b["locked_shrunk_offset"])
if __name__=="__main__":unittest.main()
