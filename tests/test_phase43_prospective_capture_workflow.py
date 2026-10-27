import unittest
from pathlib import Path

class Tests(unittest.TestCase):
    def test_prospective_capture_runs_generator_and_archive(self):
        source=Path(".github/workflows/phase43-prospective-capture.yml").read_text()
        self.assertIn("workflow_dispatch:",source)
        self.assertIn("schedule:",source)
        self.assertIn("permissions:\n  contents: read",source)
        self.assertIn("python -m scripts.phase43_multimarket_forecasts",source)
        self.assertIn("--lock-dir output/phase43_prospective/locks",source)
        self.assertIn("python -m scripts.archive_phase43_snapshot",source)
        self.assertIn("actions/upload-artifact@v4",source)
        self.assertIn("retention-days: 90",source)
if __name__=="__main__":unittest.main()
