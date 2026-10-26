"""Fail-closed pregame availability gate.

An observed player-week or roster listing is never proof of active status.
Only a separately attested, timestamped game-specific record can qualify.
"""
from datetime import datetime, timezone

VALID_STATUSES={"ACTIVE","INACTIVE","QUESTIONABLE","DOUBTFUL","OUT","UNKNOWN"}

def qualify(player, fixture, evidence, *, asof_utc):
    if asof_utc.tzinfo is None:
        raise ValueError("asof_utc must be timezone aware")
    asof=asof_utc.astimezone(timezone.utc)
    reasons=[]
    if not isinstance(evidence,dict):
        evidence={}
    required={"player_id","team","fixture_id","status","source","observed_at_utc"}
    if not required.issubset(evidence):
        reasons.append("NO_COMPLETE_GAME_SPECIFIC_AVAILABILITY_EVIDENCE")
    else:
        if any(str(evidence.get(k))!=str(v) for k,v in
               (("player_id",player["player_id"]),("team",player["team"]),
                ("fixture_id",fixture["id"]))):
            reasons.append("PLAYER_TEAM_OR_FIXTURE_MISMATCH")
        if evidence["status"] not in VALID_STATUSES:
            reasons.append("UNRECOGNIZED_STATUS")
        try:
            observed=datetime.fromisoformat(str(evidence["observed_at_utc"]).replace("Z","+00:00"))
            if observed.tzinfo is None or observed.astimezone(timezone.utc)>asof:
                reasons.append("EVIDENCE_AFTER_LOCK_OR_UNTIMESTAMPED")
        except (ValueError,TypeError):
            reasons.append("INVALID_EVIDENCE_TIMESTAMP")
        if not evidence.get("source") or not evidence.get("source_record_id"):
            reasons.append("UNTRACEABLE_EVIDENCE")
        if evidence.get("status")!="ACTIVE":
            reasons.append("NOT_OFFICIALLY_CONFIRMED_ACTIVE")
        if evidence.get("source_type")!="OFFICIAL_ACTIVE_CONFIRMATION":
            reasons.append("NOT_EXPLICIT_OFFICIAL_ACTIVE_CONFIRMATION")
    # A valid ACTIVE entry is still insufficient without a separately
    # certified starter/role and calibrated probability/price gate.
    if not reasons:
        reasons.append("STARTING_ROLE_AND_MARKET_MODEL_NOT_CERTIFIED")
    return {"player_id":player["player_id"],"fixture_id":fixture["id"],
            "status":"NO_BET","reasons":sorted(set(reasons)),
            "official_active_evidence_complete":not any(
                x for x in reasons if x!="STARTING_ROLE_AND_MARKET_MODEL_NOT_CERTIFIED"),
            "approved_units":0}
