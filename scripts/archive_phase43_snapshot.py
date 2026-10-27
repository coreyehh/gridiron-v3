"""Archive already-created Phase43 snapshots without rewriting their contents.

The GitHub Actions artifact is the time-stamped external retention boundary.
An internal SHA256 alone does not prove when a snapshot was first created.
"""
import argparse,hashlib,json,shutil
from datetime import datetime,timezone
from pathlib import Path
from scripts.phase43_multimarket_forecasts import verify

def archive(source, destination, *, now=None):
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:raise ValueError("Timezone-aware archive time required")
    source=Path(source);destination=Path(destination)
    original=source.read_bytes()
    obj=json.loads(original)
    verify(obj)
    locked=datetime.fromisoformat(obj["created_at_utc"].replace("Z","+00:00"))
    if locked.tzinfo is None or locked.astimezone(timezone.utc)>now.astimezone(timezone.utc):
        raise ValueError("Invalid snapshot lock time")
    if not obj.get("fixtures"):raise ValueError("No fixtures")
    if any(f["gameday"]<=now.date().isoformat() for f in obj["fixtures"]):
        raise ValueError("Fixture not strictly in future at archive time")
    if destination.exists():raise FileExistsError("Immutable archive already exists")
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open("xb") as handle:handle.write(original)
    return {"snapshot_path":str(destination),
            "sha256_bytes":hashlib.sha256(original).hexdigest(),
            "archive_time_utc":now.astimezone(timezone.utc).isoformat(),
            "source_lock_time_utc":locked.astimezone(timezone.utc).isoformat(),
            "snapshot_payload_sha256":obj["payload_sha256"],
            "archived_before_fixture_day":True,
            "external_timestamp_attestation":"GITHUB_ACTIONS_ARTIFACT_UPLOAD_REQUIRED",
            "betting_probabilities_calibrated":False,"approved_wagers":0}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--snapshot",required=True)
    p.add_argument("--archive",required=True)
    p.add_argument("--manifest",required=True)
    a=p.parse_args()
    m=archive(a.snapshot,a.archive)
    target=Path(a.manifest);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(m,indent=2,sort_keys=True)+"\n")
    print(json.dumps(m,indent=2))
if __name__=="__main__":main()
