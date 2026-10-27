"""Fail-closed eligibility for promoting Phase43 player forecasts.

Historical stat rows and a roster listing cannot certify game-day activation.
Only a trusted, fixture-scoped evidence adapter may provide that assertion.
"""
from scripts.phase43_snapshot_quality_audit import audit
from scripts.availability_source_verifier import verify_attestation
from datetime import datetime,timezone

def evaluate(snapshot, *, availability_verifier=None):
    quality=audit(snapshot)
    lock=datetime.fromisoformat(snapshot["created_at_utc"].replace("Z","+00:00"))
    by_fixture={}
    if len({(r["fixture_id"],r["player_id"]) for r in snapshot["forecasts"]})!=len(snapshot["forecasts"]):
        raise ValueError("Duplicate player-fixture identity")
    for r in snapshot["forecasts"]:
        fixture=r["fixture_id"]
        key=(fixture,r["player_id"])
        eligible=False
        reason="NO_TRUSTED_GAME_DAY_ACTIVE_EVIDENCE"
        if availability_verifier is not None:
            evidence=availability_verifier.get_evidence(fixture_id=fixture,
                  player_id=r["player_id"],team=r["team"])
            if (isinstance(evidence,dict) and evidence.get("status")=="ACTIVE"
                and evidence.get("source_type")=="OFFICIAL_ACTIVE_CONFIRMATION"
                and verify_attestation(availability_verifier,evidence,lock)):
                eligible=True
                reason="ACTIVE_IDENTITY_CONFIRMED_ROLE_STILL_UNVERIFIED"
        by_fixture[key]={"eligible_for_player_baseline_review":eligible,
                          "eligible_for_wager_approval":False,
                          "reason":reason}
    return {"snapshot_sha256":quality["snapshot_sha256"],
            "players_checked":len(by_fixture),
            "verified_active_count":sum(x["eligible_for_player_baseline_review"] for x in by_fixture.values()),
            "unverified_count":sum(not x["eligible_for_player_baseline_review"] for x in by_fixture.values()),
            "approved_wagers":0,
            "status":"RESEARCH_ONLY_NOT_WAGER_ELIGIBLE",
            "quality_issue_counts":quality["issue_counts"]}
