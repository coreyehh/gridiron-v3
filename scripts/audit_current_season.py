"""Fail-closed checks for current-season player-week ingestion.

This audits completed weekly stats, NOT real-time injury, roster or market data.
"""
import argparse
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pandas as pd


def validate(manifest, frame, season, min_week, max_age_days, now=None):
    now = now or datetime.now(timezone.utc)
    seasons = manifest.get("seasons", [])
    if len(seasons) != 1 or seasons[0].get("season") != season:
        raise ValueError("Current-season manifest must contain exactly requested season")
    if seasons[0].get("status") != "validated":
        raise ValueError("Current-season source is not validated")
    if frame.empty:
        raise ValueError("No current-season player-week rows")
    if set(frame["season"].dropna().astype(int)) != {season}:
        raise ValueError("Mixed or incorrect season rows")
    latest = int(frame["week"].max())
    if not frame["week"].between(1, 23).all():
        raise ValueError("Invalid NFL week range")
    if not frame["player_id"].notna().all():
        raise ValueError("Missing player IDs")
    if latest < min_week:
        raise ValueError(f"Latest available week {latest} below required {min_week}")
    if frame.duplicated(["season", "week", "player_id"]).any():
        raise ValueError("Duplicate player-week rows")
    if len(frame) != int(seasons[0]["rows"]):
        raise ValueError("Manifest and feature row counts differ")
    ts = datetime.fromisoformat(manifest["updated_at_utc"].replace("Z", "+00:00"))
    if ts.tzinfo is None or ts > now + timedelta(minutes=5):
        raise ValueError("Invalid manifest timestamp")
    if now - ts > timedelta(days=max_age_days):
        raise ValueError("Ingestion manifest is stale")
    return {"status": "VALIDATED_COMPLETED_PLAYER_WEEKS_ONLY",
            "season": season, "latest_observed_week": latest,
            "rows": len(frame), "source": seasons[0]["source"],
            "manifest_updated_at_utc": manifest["updated_at_utc"],
            "rosters_verified": False, "injuries_verified": False,
            "live_odds_verified": False, "model_approved_wagers": False}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", required=True)
    p.add_argument("--features", required=True)
    p.add_argument("--season", type=int, required=True)
    p.add_argument("--min-week", type=int, default=1)
    p.add_argument("--max-age-days", type=int, default=14)
    args = p.parse_args()
    result = validate(json.loads(Path(args.manifest).read_text()),
                      pd.read_csv(args.features), args.season,
                      args.min_week, args.max_age_days)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
