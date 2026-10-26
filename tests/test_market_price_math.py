import unittest
from scripts.market_price_math import price,american_to_decimal,two_leg_joint
class PricingTests(unittest.TestCase):
    def test_ev_at_even_money(self):
        x=price(2.0,.55,stake=10)
        self.assertAlmostEqual(x["expected_roi"],.10)
        self.assertAlmostEqual(x["expected_profit"],1)
        self.assertAlmostEqual(x["break_even_probability"],.5)
        self.assertFalse(x["probability_calibrated_by_module"])
    def test_negative_ev(self):
        self.assertLess(price(1.9,.5)["expected_roi"],0)
    def test_american_odds(self):
        self.assertAlmostEqual(american_to_decimal(-110),1+100/110)
        self.assertAlmostEqual(american_to_decimal(150),2.5)
    def test_invalid_odds(self):
        for a in (0,99,-99):
            with self.assertRaises(ValueError):american_to_decimal(a)
    def test_correlated_joint(self):
        x=two_leg_joint(.7,.6,.75)
        self.assertAlmostEqual(x["joint_probability"],.525)
        self.assertGreater(x["correlation_adjustment"],0)
    def test_joint_bounds(self):
        with self.assertRaises(ValueError):two_leg_joint(.8,.2,.9)
    def test_no_fabricated_calibration(self):
        self.assertFalse(two_leg_joint(.6,.6,.6)["joint_probability_calibrated_by_module"])
if __name__=="__main__":unittest.main()
