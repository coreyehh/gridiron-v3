import unittest
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from cryptography.fernet import Fernet
from scripts.phase41_full_slate import combine,live_capture,offline_dashboard,inspect_import
from scripts.phase40_prospective_ledger import locked_ledger,encrypted_result
from scripts.phase39_secure_quote_evidence import encrypt_fanduel_event
from test_phase39_secure_quote_evidence import row,event
from test_phase32_market_matching import snapshot,CAPTURE
KEY=Fernet.generate_key().decode()

def old_ledger():
    s=snapshot()
    cipher,_=encrypt_fanduel_event(s,event(),[row("over"),row("under")],CAPTURE,KEY)
    ledger,_=locked_ledger(s,cipher,KEY)
    return s,ledger

class Phase41Tests(unittest.TestCase):
    def test_import_locked_archive_unmodified(self):
        s,original=old_ledger()
        existing=inspect_import(encrypted_result(original,KEY),KEY,s)
        self.assertEqual(existing["lock_sha256"],original["lock_sha256"])
    def test_prior_matchups_preserved_in_combined_private_ledger(self):
        s,old=old_ledger()
        combined=combine(s,old,[])
        self.assertEqual(len(combined["entries"]),1)
        self.assertEqual(combined["entries"][0]["fanduel_line"],74.5)
        self.assertEqual(combined["entries"][0]["over_american_odds"],-110)
        self.assertFalse(combined["entries"][0]["wager_placed"])
        inspect_import(encrypted_result(combined,KEY),KEY,s)
    def test_public_board_has_no_proprietary_prices(self):
        s,old=old_ledger()
        board=offline_dashboard(s,combine(s,old,[]))
        self.assertIn("Drake London",board)
        self.assertIn("NO_CAPTURED_MARKET",board)
        self.assertNotIn("74.5",board)
        self.assertNotIn("-110",board)
        self.assertNotIn(KEY,board)
        self.assertIn("RESEARCH ONLY",board)
    def test_offline_never_accesses_paid_fetch(self):
        s,old=old_ledger()
        with patch("scripts.phase41_full_slate.fetch_json",side_effect=AssertionError("no request")):
            board=offline_dashboard(s,combine(s,old,[]))
        self.assertIn("GRIDIRON",board)
    def test_existing_fixture_never_purchased_again(self):
        s,old=old_ledger()
        def no_fetch(*args,**kwargs):raise AssertionError("Already archived, no repurchase")
        new,meta=live_capture(s,old,KEY,"synthetic-odds-key",13,"us",
                            discover_fn=lambda key,snap:[event()],fetch_fn=no_fetch)
        self.assertEqual(meta["new_requests_attempted"],0)
        self.assertEqual(new,[])
    def test_spoofed_or_past_event_excluded(self):
        s,old=old_ledger()
        expired=dict(event());expired["commence_time"]="2020-10-18T17:00:00Z"
        new,meta=live_capture(s,old,KEY,"fake-key",13,"us",
            discover_fn=lambda key,snap:[expired],fetch_fn=lambda *a:None)
        self.assertEqual(new,[])
        self.assertEqual(meta["new_requests_attempted"],0)
    def test_max_events_cap(self):
        s,old=old_ledger()
        with self.assertRaises(ValueError):
            live_capture(s,old,KEY,"fake-key",14,"us",discover_fn=lambda *a:[])
    def test_key_required_before_discovery(self):
        s,_=old_ledger()
        with self.assertRaises(ValueError):
            live_capture(s,None,"invalid-key","fake-key",1,"us",discover_fn=lambda *a:[])
    def test_reject_duplicate_market_overlap(self):
        s,old=old_ledger()
        with self.assertRaises(ValueError):combine(s,old,[old])
    def test_no_archive_does_not_invent_line(self):
        s,_=old_ledger()
        html=offline_dashboard(s,None)
        self.assertNotIn("ENCRYPTED_ARCHIVE_EXISTS",html.split('const data=')[1].split(";const $=")[0])
if __name__=="__main__":unittest.main()
