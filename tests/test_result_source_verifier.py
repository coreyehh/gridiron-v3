import unittest
from scripts.result_source_verifier import verify_results
ROW={"fixture_id":"g","player_id":"p","market":"receiving_yards",
     "actual":50,"result_verified":True,"source_name":"test",
     "source_record_id":"test-1"}
class TrustedFixture:
    def verify(self,row):
        return row["source_record_id"]=="test-1"
class Tests(unittest.TestCase):
    def test_boolean_alone_never_authenticates(self):
        with self.assertRaisesRegex(ValueError,"authentication failed"):
            verify_results([ROW])
    def test_injected_verifier(self):
        self.assertEqual(len(verify_results([ROW],verifier=TrustedFixture())),1)
    def test_missing_source_rejected(self):
        x={**ROW};del x["source_record_id"]
        with self.assertRaisesRegex(ValueError,"source evidence"):
            verify_results([x],verifier=TrustedFixture())
    def test_false_verification_flag_rejected(self):
        with self.assertRaisesRegex(ValueError,"Unverified"):
            verify_results([{**ROW,"result_verified":False}],verifier=TrustedFixture())
if __name__=="__main__":unittest.main()
