"""Export authentic Phase43 point projections into a separate immutable audit ledger.

Phase43 point estimates are NOT line-specific probabilities. This module
refuses historical reconstruction, invalid digests and nonfuture fixtures.
"""
import argparse,json,hashlib
from datetime import datetime,timezone
from pathlib import Path
from scripts.phase43_multimarket_forecasts import verify,VERSION

def export(snapshot):
    verify(snapshot)
    if snapshot.get("past_fixture_forecasts_reconstructed") is not False:
        raise ValueError("Historical reconstruction flag not trustworthy")
    locked=datetime.fromisoformat(snapshot["created_at_utc"].replace("Z","+00:00"))
    if locked.tzinfo is None:raise ValueError("Timezone-aware lock required")
    fixture_by_id={f["id"]:f for f in snapshot["fixtures"]}
    rows=[]
    seen=set()
    for player in snapshot["forecasts"]:
        fixture=fixture_by_id[player["fixture_id"]]
        if fixture["gameday"]<=locked.date().isoformat():
            raise ValueError("Not a strictly future fixture")
        for market,projection in player["point_projections"].items():
            if projection is None:continue
            key=(player["fixture_id"],player["player_id"],market)
            if key in seen:raise ValueError("Duplicate player market forecast")
            seen.add(key)
            # These are raw numerical outputs, not calibrated probabilities.
            rows.append({"fixture_id":player["fixture_id"],
                "player_id":player["player_id"],"team":player["team"],
                "market":market,"point_projection":projection,
                "forecast_at_utc":snapshot["created_at_utc"],
                "model_version":VERSION,
                "snapshot_sha256":snapshot["payload_sha256"],
                "line_specific_probability":None,
                "bookmaker_price":None,
                "approved_wager":False,
                "active_verified":player.get("active_verified") is True,
                "role_verified":player.get("role_verified") is True,
                "eligible_for_wager_approval":False,
                "eligibility_status":"RESEARCH_ONLY_UNVERIFIED_OR_UNCALIBRATED"})
    return {"source":"phase43_original_locked_snapshot",
            "snapshot_sha256":snapshot["payload_sha256"],
            "projection_count":len(rows),"projections":rows,
            "probability_calibrated":False,"approved_wagers":0}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--snapshot",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    result=export(json.loads(Path(args.snapshot).read_text()))
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise FileExistsError("Immutable export already exists")
    path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"projection_count":result["projection_count"],"approved_wagers":0}))
if __name__=="__main__":main()
