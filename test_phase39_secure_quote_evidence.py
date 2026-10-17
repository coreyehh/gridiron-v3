import json,unittest
from cryptography.fernet import Fernet
from scripts.phase39_secure_quote_evidence import (
 official_observation,fetch_official_page,encrypt_fanduel_event,decrypt_archive,
 verify_cipher_key)
from test_phase32_market_matching import snapshot,CAPTURE,KICKOFF

KEY=Fernet.generate_key().decode("ascii")
def event():
    return {"id":"event123","commence_time":KICKOFF,
      "home_team":"Atlanta Falcons","away_team":"Chicago Bears"}
def row(side="over"):
    return {"event_id":"event123","market":"receiving_yards","side":side,
       "line":74.5,"american_odds":-110,"bookmaker":"fanduel",
       "player_display_name":"Drake London",
       "kickoff_utc":KICKOFF,"quoted_at_utc":"2026-10-17T14:45:00Z",
       "captured_at_utc":CAPTURE}

class Phase39Tests(unittest.TestCase):
    def test_official_check_back_does_not_establish_active(self):
        r=official_observation(b'<html>Please check back soon for NFL Inactive Reports</html>')
        self.assertEqual(r["status"],"OFFICIAL_PAGE_HAS_NO_REPORTS")
        self.assertFalse(r["game_day_player_evidence_usable"])
        self.assertEqual(r["verified_individual_actives"],0)
    def test_embedded_scripts_are_not_player_confirmation(self):
        r=official_observation(b'<script>var active=true</script><p>NFL Inactives</p>')
        self.assertFalse(r["game_day_player_evidence_usable"])
        self.assertFalse(r["no_reports_message_detected"])
    def test_untrusted_redirect_rejected(self):
        with self.assertRaises(ValueError):
            official_observation(b"hello",source_url="https://evil.example/")
    def test_official_mock_transport_untrusted_for_player_verification(self):
        r=fetch_official_page(lambda url:(b"Check back soon",url,200))
        self.assertTrue(r["test_transport_only"])
        self.assertFalse(r["game_day_player_evidence_usable"])
    def test_fanduel_quote_roundtrip_only_with_correct_key(self):
        cipher,meta=encrypt_fanduel_event(snapshot(),event(),[row("over"),row("under")],CAPTURE,KEY)
        self.assertNotIn(b"Drake London",cipher)
        self.assertNotIn(b"74.5",cipher)
        self.assertNotIn("Drake London",json.dumps(meta))
        self.assertEqual(meta["counts"]["valid_offer_sides"],2)
        raw=decrypt_archive(cipher,KEY)
        self.assertEqual(len(raw["quotes"]),2)
        self.assertEqual(raw["quotes"][0]["player_display_name"],"Drake London")
    def test_wrong_key_refused(self):
        ciphertext,_=encrypt_fanduel_event(snapshot(),event(),[row()],CAPTURE,KEY)
        with self.assertRaises(ValueError):
            decrypt_archive(ciphertext,Fernet.generate_key().decode())
    def test_no_secret_in_artifact_manifest(self):
        _,meta=encrypt_fanduel_event(snapshot(),event(),[row()],CAPTURE,KEY)
        self.assertNotIn(KEY,json.dumps(meta))
        self.assertFalse(meta["archive_key_in_output"])
        self.assertFalse(meta["player_level_quote_publication"])
        self.assertEqual(meta["qualified_bets"],0)
    def test_key_validation_before_paid_request(self):
        for key in (None,"", "not-a-key"):
            with self.assertRaises(ValueError):verify_cipher_key(key)
    def test_other_bookmaker_not_in_archive(self):
        r=row();r["bookmaker"]="draftkings"
        with self.assertRaises(ValueError):encrypt_fanduel_event(snapshot(),event(),[r],CAPTURE,KEY)
    def test_foreign_event_not_in_archive(self):
        r=row();r["event_id"]="other"
        with self.assertRaises(ValueError):encrypt_fanduel_event(snapshot(),event(),[r],CAPTURE,KEY)
    def test_postkickoff_rejected(self):
        with self.assertRaises(ValueError):
            encrypt_fanduel_event(snapshot(),event(),[row()],"2026-10-18T19:00:00Z",KEY)
    def test_snapshot_tamper_rejected(self):
        s=snapshot();s["forecasts"][0]["targets"]=1234
        with self.assertRaises(ValueError):
            encrypt_fanduel_event(s,event(),[row()],CAPTURE,KEY)
    def test_quotes_capped(self):
        with self.assertRaises(ValueError):
            encrypt_fanduel_event(snapshot(),event(),[row()]*10001,CAPTURE,KEY)
if __name__=="__main__":unittest.main()
