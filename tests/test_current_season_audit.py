"""Offline fail-closed tests for 2026 current-season ingest audit."""
import unittest
from datetime import datetime, timedelta, timezone
import pandas as pd
from scripts.audit_current_season import validate

NOW = datetime(2026, 10, 26, tzinfo=timezone.utc)

def fixture(week=7, rows=2, age=0):
    frame = pd.DataFrame({
        "season": [2026] * rows,
        "week": [week] * rows,
        "player_id": [f"id-{i}" for i in range(rows)],
    })
    manifest = {
        "seasons": [{"season": 2026, "rows": rows, "status": "validated",
                     "source": "https://example.test/stats.parquet"}],
        "updated_at_utc": (NOW - timedelta(days=age)).isoformat(),
        "feature_rows": rows,
        "unidentified_player_week_rows_quarantined": 0,
    }
    return manifest, frame

class CurrentSeasonAuditTests(unittest.TestCase):
    def test_valid_completed_weeks_not_live_verified(self):
        m, f = fixture()
        result = validate(m, f, 2026, 6, 14, now=NOW)
        self.assertEqual(result["latest_observed_week"], 7)
        self.assertFalse(result["model_approved_wagers"])
        self.assertFalse(result["rosters_verified"])

    def test_reject_old_week(self):
        m, f = fixture(week=4)
        with self.assertRaises(ValueError):
            validate(m, f, 2026, 6, 14, now=NOW)

    def test_reject_stale_manifest(self):
        m, f = fixture(age=15)
        with self.assertRaises(ValueError):
            validate(m, f, 2026, 6, 14, now=NOW)

    def test_reject_wrong_season(self):
        m, f = fixture()
        f.loc[0, "season"] = 2025
        with self.assertRaises(ValueError):
            validate(m, f, 2026, 6, 14, now=NOW)

    def test_reject_duplicate_player_week(self):
        m, f = fixture()
        f.loc[1, "player_id"] = f.loc[0, "player_id"]
        with self.assertRaises(ValueError):
            validate(m, f, 2026, 6, 14, now=NOW)

    def test_accept_documented_quarantine(self):
        m, f = fixture()
        m["seasons"][0]["rows"] = 3
        m["unidentified_player_week_rows_quarantined"] = 1
        result = validate(m, f, 2026, 6, 14, now=NOW)
        self.assertEqual(result["quarantined_unidentified_rows"], 1)

    def test_reject_row_count_mismatch(self):
        m, f = fixture()
        m["seasons"][0]["rows"] = 999
        with self.assertRaises(ValueError):
            validate(m, f, 2026, 6, 14, now=NOW)

    def test_reject_future_timestamp(self):
        m, f = fixture()
        m["updated_at_utc"] = (NOW + timedelta(hours=2)).isoformat()
        with self.assertRaises(ValueError):
            validate(m, f, 2026, 6, 14, now=NOW)

if __name__ == "__main__":
    unittest.main()
