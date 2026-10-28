"""Normalize externally supplied game-day availability attestations.

This adapter DOES NOT download or certify official data. It only accepts a
source-labeled export, checks its structure, and forwards records to the
fail-closed availability gate. No claim of live roster verification is made.
"""
import argparse,json
from datetime import datetime,timezone
from pathlib import Path
from scripts.pregame_availability_gate import qualify
from scripts.availability_source_verifier import DenyAllVerifier,verify_attestation

def normalize(payload, *, asof_utc, verifier=None):
    if asof_utc.tzinfo is None:raise ValueError("UTC-aware asof required")
    if not isinstance(payload,dict) or not isinstance(payload.get("fixtures"),list):
        raise ValueError("Expected fixtures array")
    if verifier is None:verifier=DenyAllVerifier()
    results=[]
    seen=set()
    for fixture in payload["fixtures"]:
        if not isinstance(fixture,dict) or not isinstance(fixture.get("id"),str):
            raise ValueError("Fixture must have an ID")
        for player in fixture.get("players",[]):
            if not isinstance(player,dict) or not all(k in player for k in ("player_id","team")):
                raise ValueError("Player must have player_id and team")
            key=(fixture["id"],str(player["player_id"]))
            if key in seen:raise ValueError("Duplicate player-fixture availability")
            seen.add(key)
            supplied=player.get("evidence")
            # Never trust a caller-supplied authentication boolean.
            # Until a trusted source verifier is integrated, every
            # external record is treated as unauthenticated.
            evidence=dict(supplied) if isinstance(supplied,dict) else supplied
            if isinstance(evidence,dict):
                evidence["source_authenticated"]=verify_attestation(verifier,evidence,asof_utc)
            result=qualify(player,fixture,evidence,asof_utc=asof_utc)
            results.append(result)
    return {"status":"AVAILABILITY_GATE_EVALUATED_NO_BETS_APPROVED",
            "asof_utc":asof_utc.astimezone(timezone.utc).isoformat(),
            "player_fixture_count":len(results),
            "official_active_evidence_complete_count":sum(x["official_active_evidence_complete"] for x in results),
            "approved_wagers":0,"results":results,
            "source_verified_by_adapter":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--asof-utc",required=True)
    a=p.parse_args()
    asof=datetime.fromisoformat(a.asof_utc.replace("Z","+00:00"))
    result=normalize(json.loads(Path(a.input).read_text()),asof_utc=asof)
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2))
    print(json.dumps({"status":result["status"],"player_fixture_count":result["player_fixture_count"],
                      "approved_wagers":0},indent=2))
if __name__=="__main__":main()
