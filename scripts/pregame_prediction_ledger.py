"""Append-only pregame prediction ledger with deterministic IDs.

Only records explicitly captured before kickoff qualify for later evaluation.
The ledger is an input/output utility, not a live sportsbook data source.
"""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path

FIELDS=("fixture_id","player_id","market","selection","probability",
        "forecast_at_utc","kickoff_utc","model_version")
def _utc(value):
    d=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if d.tzinfo is None:raise ValueError("Timezone-aware timestamps required")
    return d.astimezone(timezone.utc)
def validate(record):
    if any(record.get(k) is None for k in FIELDS):
        raise ValueError("Missing required forecast fields")
    p=float(record["probability"])
    if not 0<=p<=1:raise ValueError("Probability outside [0,1]")
    if _utc(record["forecast_at_utc"])>=_utc(record["kickoff_utc"]):
        raise ValueError("Forecast must precede kickoff")
    if record.get("outcome") is not None:
        raise ValueError("Outcome must not be recorded in pregame snapshot")
    return True
def fingerprint(record):
    payload={k:record[k] for k in FIELDS}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def append(path,record):
    validate(record)
    target=Path(path);target.parent.mkdir(parents=True,exist_ok=True)
    entry={**record,"forecast_id":fingerprint(record)}
    if target.exists():
        for line in target.read_text().splitlines():
            if line.strip() and json.loads(line).get("forecast_id")==entry["forecast_id"]:
                raise ValueError("Duplicate immutable forecast")
    with target.open("a") as f:f.write(json.dumps(entry,sort_keys=True)+"\n")
    return entry
def attach_outcomes(forecasts,outcomes):
    """Join external verified results without mutating pregame records."""
    lookup={}
    for item in outcomes:
        fid=item["forecast_id"]
        if fid in lookup:raise ValueError("Duplicate result")
        if item.get("result_verified") is not True:raise ValueError("Unverified result")
        if item.get("outcome") not in (0,1):raise ValueError("Invalid outcome")
        lookup[fid]=item["outcome"]
    rows=[]
    for record in forecasts:
        validate(record)
        fid=fingerprint(record)
        if fid in lookup:
            rows.append({**record,"outcome":lookup[fid]})
    return rows
