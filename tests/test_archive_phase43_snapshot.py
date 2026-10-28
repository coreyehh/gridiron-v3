import json,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
from scripts.archive_phase43_snapshot import archive
from scripts.phase43_multimarket_forecasts import VERSION
from scripts.phase31_accountability import digest
NOW=datetime(2026,10,26,12,tzinfo=timezone.utc)
def snap(gameday="2026-10-28"):
    x={"version":VERSION,"created_at_utc":"2026-10-26T10:00:00Z",
       "fixtures":[{"id":"g","gameday":gameday}],"forecasts":[],
       "past_fixture_forecasts_reconstructed":False}
    x["payload_sha256"]=digest(x)
    return x
class Tests(unittest.TestCase):
    def test_preserves_exact_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/"s.json";dst=Path(d)/"archive.json"
            src.write_text(json.dumps(snap(),indent=3))
            manifest=archive(src,dst,now=NOW)
            self.assertEqual(src.read_bytes(),dst.read_bytes())
            self.assertEqual(manifest["approved_wagers"],0)
            with self.assertRaises(FileExistsError):archive(src,dst,now=NOW)
    def test_reject_fixture_today(self):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/"s.json";src.write_text(json.dumps(snap("2026-10-26")))
            with self.assertRaisesRegex(ValueError,"future"):archive(src,Path(d)/"out",now=NOW)
    def test_reject_tampered_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/"s.json";x=snap();x["created_at_utc"]="2026-10-25T10:00:00Z"
            src.write_text(json.dumps(x))
            with self.assertRaisesRegex(ValueError,"digest"):archive(src,Path(d)/"out",now=NOW)
if __name__=="__main__":unittest.main()
