import copy,unittest
from cryptography.fernet import Fernet
from scripts.phase39_secure_quote_evidence import encrypt_fanduel_event
from scripts.phase40_prospective_ledger import (
 locked_ledger,settle,encrypted_result,open_archive)
from test_phase39_secure_quote_evidence import event,row
from test_phase32_market_matching import snapshot,CAPTURE

KEY=Fernet.generate_key().decode()
def sample():
    s=snapshot()
    cipher,_=encrypt_fanduel_event(s,event(),[row("over"),row("under")],CAPTURE,KEY)
    return s,cipher
def final():
    return {"fixture_id":"2026-W06-CHI-at-ATL","final_scores_verified":True,
      "source":"unit_test_fixture"}

class Phase40Tests(unittest.TestCase):
    def test_one_matched_pair_is_prelocked_and_private(self):
        s,cipher=sample()
        led,a=locked_ledger(s,cipher,KEY)
        self.assertEqual(len(led["entries"]),1)
        self.assertEqual(a["entries_locked"],1)
        self.assertEqual(led["entries"][0]["projection_minus_line"],5.5)
        self.assertFalse(led["entries"][0]["bet_promoted"])
        self.assertEqual(a["official_bets"],0)
        self.assertNotIn("Drake London",str(a))
        self.assertNotIn("74.5",str(a))
    def test_encrypted_ledger_has_no_plaintext(self):
        s,cipher=sample();led,_=locked_ledger(s,cipher,KEY)
        encrypted=encrypted_result(led,KEY)
        self.assertNotIn(b"Drake London",encrypted)
        self.assertNotIn(b"74.5",encrypted)
    def test_wrong_key_fails(self):
        s,cipher=sample()
        with self.assertRaises(ValueError):
            locked_ledger(s,cipher,Fernet.generate_key().decode())
    def test_snapshot_mismatch_fails(self):
        s,cipher=sample();s2=snapshot()
        s2["forecasts"][0]["receiving_yards"]=100
        from scripts.phase31_accountability import digest
        s2["payload_sha256"]=digest({k:v for k,v in s2.items() if k!="payload_sha256"})
        with self.assertRaises(ValueError):locked_ledger(s2,cipher,KEY)
    def test_no_final_no_grading(self):
        s,cipher=sample();ledger,_=locked_ledger(s,cipher,KEY)
        score,report=settle(ledger,{("ATL","gsis1"):{"receiving_yards":105}},
               {"fixture_id":ledger["fixture_id"],"final_scores_verified":False})
        self.assertIsNone(score)
        self.assertEqual(report["graded"],0)
    def test_over_hit(self):
        s,cipher=sample();ledger,_=locked_ledger(s,cipher,KEY)
        score,report=settle(ledger,{("ATL","gsis1"):{"receiving_yards":82}},final(),
                                "2026-10-18T21:00:00Z")
        self.assertEqual(report["graded"],1)
        self.assertEqual(score["graded"][0]["over_result"],"WIN")
        self.assertEqual(score["graded"][0]["under_result"],"LOSS")
        self.assertIsNone(score["roi"])
    def test_under_hit(self):
        s,cipher=sample();ledger,_=locked_ledger(s,cipher,KEY)
        score,report=settle(ledger,{("ATL","gsis1"):{"receiving_yards":43}},final())
        self.assertEqual(score["graded"][0]["under_result"],"WIN")
    def test_missing_box_never_inferred_zero(self):
        s,cipher=sample();ledger,_=locked_ledger(s,cipher,KEY)
        score,report=settle(ledger,{},final())
        self.assertEqual(report["unresolved"],1)
        self.assertEqual(report["graded"],0)
        self.assertEqual(score["graded"],[])
    def test_cannot_modify_locked_ledger(self):
        s,cipher=sample();ledger,_=locked_ledger(s,cipher,KEY)
        ledger["entries"][0]["frozen_projection"]=999
        with self.assertRaises(ValueError):settle(ledger,{},final())
    def test_before_kickoff_never_scores(self):
        s,cipher=sample();ledger,_=locked_ledger(s,cipher,KEY)
        result,report=settle(ledger,{},final(),"2026-10-17T15:00:00Z")
        self.assertIsNone(result)
        self.assertEqual(report["status"],"WAITING_FOR_KICKOFF")
    def test_unpaired_does_not_become_market(self):
        s=snapshot()
        cipher,_=encrypt_fanduel_event(s,event(),[row("over")],CAPTURE,KEY)
        ledger,manifest=locked_ledger(s,cipher,KEY)
        self.assertEqual(manifest["entries_locked"],0)
    def test_source_quote_date_before_frozen_lock_not_promotable(self):
        s=snapshot()
        rows=[row("over"),row("under")]
        for r in rows:r["quoted_at_utc"]="2026-10-17T12:59:00Z"
        # phase39 rejects older than freshness window. For any archive that
        # does pass, Phase40 still marks no wager no EV.
        with self.assertRaises(ValueError):
            encrypt_fanduel_event(s,event(),rows,CAPTURE,KEY)
if __name__=="__main__":unittest.main()
