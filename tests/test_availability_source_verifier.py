import unittest
from datetime import datetime,timezone,timedelta
from scripts.availability_source_verifier import Attestation,DenyAllVerifier,verify_attestation
NOW=datetime(2026,10,26,23,tzinfo=timezone.utc)
E={"fixture_id":"game","player_id":"p1","team":"CIN","source_record_id":"r1","source":"official"}
class FakeVerifier:
    def __init__(self,**overrides):self.overrides=overrides
    def attest(self,*,evidence,asof_utc):
        d=dict(fixture_id="game",player_id="p1",team="CIN",
            source_record_id="r1",source_name="official",
            observed_at_utc=(NOW-timedelta(minutes=1)).isoformat(),authenticated=True)
        d.update(self.overrides)
        return Attestation(**d)
class Tests(unittest.TestCase):
    def test_deny_by_default(self):
        self.assertFalse(verify_attestation(DenyAllVerifier(),E,NOW))
    def test_valid_attestation_contract(self):
        self.assertTrue(verify_attestation(FakeVerifier(),E,NOW))
    def test_reject_wrong_player(self):
        self.assertFalse(verify_attestation(FakeVerifier(player_id="p2"),E,NOW))
    def test_reject_future_evidence(self):
        self.assertFalse(verify_attestation(FakeVerifier(observed_at_utc=(NOW+timedelta(minutes=1)).isoformat()),E,NOW))
    def test_reject_unverified_claim(self):
        self.assertFalse(verify_attestation(FakeVerifier(authenticated=False),E,NOW))
    def test_reject_untraceable_source(self):
        self.assertFalse(verify_attestation(FakeVerifier(source_name=""),E,NOW))
if __name__=="__main__":unittest.main()
