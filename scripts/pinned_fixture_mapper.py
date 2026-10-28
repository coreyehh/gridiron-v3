"""Derive fixture/week mapping from a pinned NFL schedule source.

Fixture IDs must match the original Phase43 convention. Only completed
regular-season fixtures can be reconciled. Hash pinning alone does not certify
the schedule provider's authenticity.
"""
import hashlib
from pathlib import Path
import pandas as pd

def fixture_weeks(schedule_path, *, expected_sha256, season=2026):
    data=Path(schedule_path).read_bytes()
    if not expected_sha256 or hashlib.sha256(data).hexdigest()!=expected_sha256:
        raise ValueError("Schedule source hash mismatch")
    path=str(schedule_path).lower()
    if path.endswith(".csv"):frame=pd.read_csv(schedule_path)
    elif path.endswith(".parquet"):frame=pd.read_parquet(schedule_path)
    else:raise ValueError("Unsupported schedule format")
    needed={"season","week","game_type","home_team","away_team","home_score","away_score"}
    if not needed.issubset(frame.columns):raise ValueError("Schedule missing required fields")
    games=frame[(frame.season==season)&(frame.game_type=="REG")].copy()
    mapping={}
    for r in games.itertuples(index=False):
        if pd.isna(r.home_score) or pd.isna(r.away_score):continue
        if not 1<=int(r.week)<=18:raise ValueError("Invalid regular-season week")
        fid=f"{season}-W{int(r.week):02d}-{r.away_team}-at-{r.home_team}"
        if fid in mapping:raise ValueError("Duplicate completed fixture")
        mapping[fid]=(season,int(r.week))
    return mapping
