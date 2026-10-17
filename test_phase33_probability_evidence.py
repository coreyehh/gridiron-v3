import unittest
from unittest.mock import patch
from scripts.phase33_probability_evidence import (
 residual_probability,official_availability_gate,prequential,
 frozen_threshold_audit,markdown,MIN_RESIDUALS)
from test_phase23_role_model import sample
from test_phase32_market_matching import snapshot

class Phase33Tests(unittest.TestCase):
    def test_unsupported_sample_no_probability(self):
        self.assertIsNone(residual_probability([0.]*(MIN_RESIDUALS-1),3.0,2.5))
    def test_frequencies_are_smoothed_and_finite(self):
        r=residual_probability([0.]*MIN_RESIDUALS,4.,3.5)
        self.assertGreater(r["p_over"],.9)
        self.assertLess(r["p_over"],1.)
        self.assertTrue(0<=r["sampling_interval_95pct"][0]<=r["sampling_interval_95pct"][1]<=1)
        self.assertFalse(r["calibrated_to_offered_lines"])
    def test_invalid_lines_fail_closed(self):
        with self.assertRaises(ValueError):residual_probability([0.]*100,2.,float("nan"))
        with self.assertRaises(ValueError):residual_probability([0.]*100,2.,-1.)
    def test_outlier_probability_only_changes_when_training_does(self):
        history=[0.]*100
        first=residual_probability(history,3.,2.5)
        self.assertNotEqual(first["p_over"],
            residual_probability(history+[-100.],3.,2.5)["p_over"])
        self.assertEqual(len(history),100)
    def test_availability_never_inferred_from_unverified_boolean(self):
        for evidence in (None,{"active":True},{"provider":"unknown","active":True},
                         {"official_active_verified":True}):
            gate=official_availability_gate(evidence)
            self.assertFalse(gate["eligible"])
            self.assertFalse(gate["official_active_verified"])
    def test_missing_week_box_not_assigned_fake_zero(self):
        h,s=sample()
        remove=h[(h.season==2026)&(h.week==4)].index
        absent=h.drop(remove)
        out=prequential(absent,s,4,4)
        self.assertGreater(out["missing_box_rows_excluded"],0)
        self.assertFalse(out["matched_actual_bookmaker_line_calibration_proven"])
        self.assertEqual(out["qualified_bets"],0)
    def test_same_week_outcomes_do_not_generate_same_week_calibration(self):
        h,s=sample()
        a=prequential(h,s,4,4)
        tampered=h.copy()
        idx=tampered[(tampered.season==2026)&(tampered.week==4)].index
        tampered.loc[idx,"receiving_yards"]=999.
        b=prequential(tampered,s,4,4)
        self.assertEqual(a["scores"],b["scores"])
        self.assertEqual(a["evaluated_completed_weeks"],b["evaluated_completed_weeks"])
    def test_frozen_forecasts_research_thresholds_only(self):
        frozen=snapshot()
        result=frozen_threshold_audit(frozen,
            {"receptions":[0.]*MIN_RESIDUALS,"receiving_yards":[0.]*MIN_RESIDUALS},
            {"receptions":3.5,"receiving_yards":54.5})
        self.assertEqual(result["counts"]["threshold_comparisons"],4)
        self.assertFalse(result["calibrated_real_market_probabilities"])
        self.assertEqual(result["eligible_bets"],0)
    def test_diagnostics_explicitly_disallow_book_claims(self):
        h,s=sample()
        out=prequential(h,s,4,4)
        doc=markdown(out)
        self.assertIn("NOT VERIFIED",doc)
        self.assertIn("0.",doc)
        self.assertEqual(out["qualified_bets"],0)
if __name__=="__main__":unittest.main()
