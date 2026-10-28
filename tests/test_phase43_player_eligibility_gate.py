import unittest
from scripts.phase43_player_eligibility_gate import evaluate
from scripts.availability_source_verifier import Attestation
from scripts.phase43_multimarket_forecasts import VERSION
from scripts.phase31_accountability import digest
def snapshot():
    x={"version":VERSION,"created_at_utc":"2026-10-18T12:00:00Z",
       "fixtures":[{"id":"2026-W06-WAS-at-SF","home":"SF","away":"WAS","gameday":"2026-10-19"}],
       "forecasts":[{"fixture_id":"2026-W06-WAS-at-SF","player_id":"p1",
                     "player_name":"Player","team":"WAS","active_verified":False,
                     "role_verified":False,"last_observed_season":2026,
                     "last_observed_week":5,"point_projections":{"rushing_yards":12.0}}],
       "past_fixture_forecasts_reconstructed":False}
    x["payload_sha256"]=digest(x)
    return x
class FakeVerifier:
    def get_evidence(self,**kwargs):
        return {**kwargs,"status":"ACTIVE","source_type":"OFFICIAL_ACTIVE_CONFIRMATION",
                "source":"trusted_fixture","source_record_id":"record1",
                "observed_at_utc":"2026-10-18T11:00:00Z"}
    def attest(self,*,evidence,asof_utc):
        return Attestation(fixture_id=evidence["fixture_id"],
          player_id=evidence["player_id"],team=evidence["team"],
          source_record_id=evidence["source_record_id"],
          observed_at_utc=evidence["observed_at_utc"],
          source_name=evidence["source"],authenticated=True)
class UntrustedVerifier(FakeVerifier):
    def attest(self,*,evidence,asof_utc):
        return None
class Tests(unittest.TestCase):
    def test_default_denies_all(self):
        x=evaluate(snapshot())
        self.assertEqual(x["verified_active_count"],0)
        self.assertEqual(x["approved_wagers"],0)
    def test_trusted_active_still_not_approved(self):
        x=evaluate(snapshot(),availability_verifier=FakeVerifier())
        self.assertEqual(x["verified_active_count"],1)
        self.assertEqual(x["approved_wagers"],0)
    def test_untrusted_active_flag_rejected(self):
        x=evaluate(snapshot(),availability_verifier=UntrustedVerifier())
        self.assertEqual(x["verified_active_count"],0)
    def test_tampered_snapshot_rejected(self):
        s=snapshot();s["forecasts"][0]["team"]="DAL"
        with self.assertRaisesRegex(ValueError,"digest"):evaluate(s)
if __name__=="__main__":unittest.main()
