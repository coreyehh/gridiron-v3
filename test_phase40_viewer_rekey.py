import unittest
from cryptography.fernet import Fernet
from scripts.phase40_viewer_rekey import rekey
from scripts.phase40_prospective_ledger import locked_ledger,encrypted_result
from scripts.phase39_secure_quote_evidence import encrypt_fanduel_event
from test_phase39_secure_quote_evidence import row,event
from test_phase32_market_matching import snapshot,CAPTURE
class RotationTests(unittest.TestCase):
    def setUp(self):
        self.old=Fernet.generate_key().decode()
        self.new=Fernet.generate_key().decode()
        s=snapshot()
        cipher,_=encrypt_fanduel_event(s,event(),[row("over"),row("under")],CAPTURE,self.old)
        ledger,_=locked_ledger(s,cipher,self.old)
        self.encrypted=encrypted_result(ledger,self.old)
    def test_rotate_preserves_viewer_rows(self):
        out,meta=rekey(self.encrypted,self.old,self.new)
        self.assertEqual(meta["entry_count"],1)
        self.assertNotIn(b"Drake London",out)
        self.assertNotIn("Drake London",str(meta))
        self.assertEqual(Fernet(self.new).decrypt(out),Fernet(self.old).decrypt(self.encrypted))
    def test_original_key_cannot_decrypt_rotated_file(self):
        from cryptography.fernet import InvalidToken
        out,_=rekey(self.encrypted,self.old,self.new)
        with self.assertRaises(InvalidToken):Fernet(self.old).decrypt(out)
    def test_wrong_old_key_fails(self):
        with self.assertRaises(ValueError):
            rekey(self.encrypted,Fernet.generate_key().decode(),self.new)
    def test_reusing_same_key_rejected(self):
        with self.assertRaises(ValueError):rekey(self.encrypted,self.old,self.old)
    def test_corrupted_source_rejected(self):
        with self.assertRaises(ValueError):rekey(b"bad",self.old,self.new)
if __name__=="__main__":unittest.main()
