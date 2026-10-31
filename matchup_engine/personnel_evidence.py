"""Independent evidence checks for manual personnel scenario inputs.

Sources must be explicitly provided and dated. No guessed roster statuses.
"""
from urllib.parse import urlparse
import pandas as pd

def audit_personnel_evidence(adjustments, as_of, max_age_hours=168):
    needed={"game_id","team","source","observed_at","reason","points_adjustment"}
    missing=needed-set(adjustments.columns)
    if missing:
        raise ValueError(f"Missing evidence fields: {sorted(missing)}")
    if adjustments.empty:
        return pd.DataFrame(columns=["game_id","team","evidence_age_hours","evidence_status"])
    records=adjustments.copy()
    times=pd.to_datetime(records.observed_at,utc=True,errors="raise")
    cutoff=pd.Timestamp(as_of)
    cutoff=cutoff.tz_localize("UTC") if cutoff.tzinfo is None else cutoff.tz_convert("UTC")
    age=(cutoff-times).dt.total_seconds()/3600
    if age.lt(0).any():
        raise ValueError("Future-dated personnel evidence")
    if age.gt(max_age_hours).any():
        raise ValueError("Stale personnel evidence")
    if records.source.isna().any() or records.reason.isna().any():
        raise ValueError("Evidence must include source and reason")
    if any(not str(s).strip() or not str(r).strip() for s,r in zip(records.source,records.reason)):
        raise ValueError("Blank evidence source or reason")
    # A source reference is required; it is not claimed to be independently verified.
    out=records[["game_id","team"]].copy()
    out["evidence_age_hours"]=age.to_numpy()
    out["evidence_status"]="PROVIDED_SOURCE_NOT_INDEPENDENTLY_VERIFIED"
    return out
