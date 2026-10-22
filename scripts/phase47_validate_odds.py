#!/usr/bin/env python3
"""Phase 47: strict, append-only-ready pregame odds validation. No odds are fabricated."""
import argparse
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

REQUIRED = ("player_id", "season", "week", "market", "direction", "line",
            "american_odds", "quoted_at_utc", "kickoff_utc", "sportsbook")
VALID_DIRECTIONS = {"over", "under"}
VALID_MARKETS = {"rushing_attempts", "rushing_yards", "receptions",
                 "receiving_yards", "passing_attempts", "passing_yards"}

def parse_utc(value):
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return dt.astimezone(timezone.utc)

def validate(row, max_age_hours=24):
    missing = [key for key in REQUIRED if not str(row.get(key, "")).strip()]
    if missing:
        raise ValueError("missing fields: " + ", ".join(missing))
    if row["direction"].lower() not in VALID_DIRECTIONS:
        raise ValueError("unsupported direction")
    if row["market"].lower() not in VALID_MARKETS:
        raise ValueError("unsupported market")
    if not str(row["player_id"]).strip() or not str(row["sportsbook"]).strip():
        raise ValueError("missing identity or sportsbook")
    if int(row["season"]) < 2000 or not 1 <= int(row["week"]) <= 22:
        raise ValueError("invalid season/week")
    line = float(row["line"])
    if not 0 <= line < 10000:
        raise ValueError("invalid line")
    odds = int(row["american_odds"])
    if odds == 0 or -100 < odds < 100:
        raise ValueError("invalid American odds")
    quote, kickoff = parse_utc(row["quoted_at_utc"]), parse_utc(row["kickoff_utc"])
    if quote >= kickoff:
        raise ValueError("post-kickoff quote / leakage")
    if kickoff - quote > timedelta(hours=max_age_hours):
        raise ValueError("stale quote")
    return dict(row, quoted_at_utc=quote.isoformat(), kickoff_utc=kickoff.isoformat(),
                american_odds=odds, line=line, season=int(row["season"]), week=int(row["week"]))

def process(source, accepted, rejected, max_age_hours=24):
    rows = list(csv.DictReader(Path(source).open(newline="", encoding="utf-8")))
    good, bad = [], []
    for index, row in enumerate(rows, start=2):
        try:
            good.append(validate(row, max_age_hours))
        except (ValueError, TypeError, OverflowError) as exc:
            bad.append({"source_row": index, "reason": str(exc), "record": row})
    Path(accepted).parent.mkdir(parents=True, exist_ok=True)
    with Path(accepted).open("w", encoding="utf-8") as f:
        for item in good:
            f.write(json.dumps(item, sort_keys=True) + "\n")
    Path(rejected).write_text(json.dumps(bad, indent=2) + "\n", encoding="utf-8")
    return len(good), len(bad)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--accepted", required=True)
    parser.add_argument("--rejected", required=True)
    parser.add_argument("--max-age-hours", type=float, default=24)
    args = parser.parse_args()
    ok, bad = process(args.input, args.accepted, args.rejected, args.max_age_hours)
    print(f"accepted={ok} rejected={bad}")
    if bad:
        raise SystemExit(1)
