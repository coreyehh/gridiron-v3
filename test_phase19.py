import tempfile,unittest
from pathlib import Path
from cryptography.fernet import Fernet
from scripts.phase19 import (select_event,freeze_before_quotes,open_forecasts,
    reconcile,seal_comparisons,decrypt_archive,validate_key)

EVENT={"id":"E","home_team":"Los Angeles Rams","away_team":"Buffalo Bills",
       "commence_time":"2026-10-13T00:15:00Z"}
LOCK="2026-10-12T19:00:00Z"
P={"event_id":"E","player_id":"gsis1","market":"receptions",
   "point_projection":5.1,"created_at_utc":"2026-10-12T18:55:00Z"}
ROSTER=[{"player_id":"gsis1","player_name":"Example Receiver",
         "team":"BUF","season":2026,"source":"fixture","source_ref":"fixture",
         "as_of_utc":"2026-10-12T18:00:00Z"}]
def quote(last_update,market="receptions"):
 return {"event_id":"E","season":2026,"home_team":"Los Angeles Rams",
       "away_team":"Buffalo Bills","player_display_name":"Example Receiver",
       "market":market,"line":4.5,"quoted_at_utc":last_update,
       "captured_at_utc":"2026-10-12T19:05:00Z",
       "kickoff_utc":"2026-10-13T00:15:00Z","bookmaker":"fanduel",
       "american_odds":-110,"side":"over"}
class Phase19Tests(unittest.TestCase):
 def test_select_explicit_matchup_without_home_guess(self):
  self.assertEqual(select_event([EVENT],"BUF","LA",at=LOCK)["id"],"E")
  self.assertEqual(select_event([EVENT],"Buffalo Bills","Los Angeles Rams",at=LOCK)["id"],"E")
  with self.assertRaises(ValueError):select_event([EVENT],"BUF","KC",at=LOCK)
  with self.assertRaises(ValueError):select_event([EVENT,EVENT],"BUF","LA",at=LOCK)
 def test_encryption_lock_roundtrip_and_no_plaintext(self):
  key=validate_key(Fernet.generate_key().decode())
  with tempfile.TemporaryDirectory() as d:
   l=freeze_before_quotes([P],EVENT,{"allowed_completed_2026_weeks":[1,2,3,4]},Path(d),key,LOCK)
   self.assertNotIn(b"gsis1",Path(l["file"]).read_bytes())
   restored=open_forecasts(l,key)
   self.assertEqual(restored["predictions"][0]["point_projection"],5.1)
   rows,report=reconcile(restored,[quote("2026-10-12T18:58:00Z"),quote("2026-10-12T19:02:00Z")],ROSTER)
   self.assertEqual(report["observed_after_lock"],2)
   self.assertEqual(report["existing_price_observed_after_lock"],1)
   self.assertEqual(report["updated_after_lock"],1)
   file=seal_comparisons(restored,rows,report,Path(d),key)
   doc=decrypt_archive(file,key._signing_key.hex()) if False else None
   self.assertNotIn(b"Example Receiver",file.read_bytes())
   self.assertEqual(len(key.decrypt(file.read_bytes()))>100,True)
 def test_old_quote_observed_after_lock_accepted_and_classified(self):
  frozen={"event_id":"E","locked_at_utc":LOCK,"predictions":[P]}
  rec,summary=reconcile(frozen,[quote("2026-10-12T18:50:00Z")],ROSTER)
  self.assertEqual(len(rec),1)
  self.assertFalse(rec[0]["book_quote_updated_after_lock"])
  self.assertEqual(summary["observed_after_lock"],1)
 def test_capture_must_follow_lock(self):
  frozen={"event_id":"E","locked_at_utc":LOCK,"predictions":[P]}
  with self.assertRaises(ValueError):
   reconcile(frozen,[{**quote("2026-10-12T18:40:00Z"),
     "captured_at_utc":"2026-10-12T18:58:00Z"}],ROSTER)
 def test_quotes_never_promoted_to_bets(self):
  frozen={"event_id":"E","locked_at_utc":LOCK,"predictions":[P]}
  rows,report=reconcile(frozen,[quote("2026-10-12T19:02:00Z")],ROSTER)
  self.assertEqual(rows[0]["decision"],"INSUFFICIENT_DATA")
  self.assertIsNone(rows[0]["model_probability"])
  self.assertEqual(report["official_bets"],0)
 def test_forecast_generated_after_lock_rejected(self):
  key=validate_key(Fernet.generate_key().decode())
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):
    freeze_before_quotes([{**P,"created_at_utc":"2026-10-12T19:01:00Z"}],
      EVENT,{},Path(d),key,LOCK)
 def test_missing_key_fails_closed(self):
  with self.assertRaises(ValueError):validate_key(None)
  with self.assertRaises(ValueError):validate_key("nonsense")
if __name__=="__main__":unittest.main()
