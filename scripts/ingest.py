"""GRIDIRON: source-tracked nflverse player-week import, no future-game data in lag features."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
import shutil
import pandas as pd

URL = "https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_{year}.parquet"
REQUIRED = {"season", "week", "player_id", "receptions", "receiving_yards",
            "rushing_yards", "passing_yards", "position"}
MEASURES = ("receptions", "receiving_yards", "rushing_yards", "passing_yards")

def download(year, folder):
    source = URL.format(year=year)
    destination = folder / ("stats_player_week_%d.parquet" % year)
    request = Request(source, headers={"User-Agent": "GRIDIRON-v3/1.0"})
    with urlopen(request, timeout=120) as response, destination.open("wb") as out:
        shutil.copyfileobj(response, out)
    data = pd.read_parquet(destination)
    missing = sorted(REQUIRED.difference(data.columns))
    if missing:
        raise ValueError("Season %d missing columns: %s" % (year, missing))
    if data.empty or set(data.season.dropna().astype(int)) != {year}:
        raise ValueError("Season %d contains unexpected data" % year)
    if not data.week.between(1, 23).all():
        raise ValueError("Invalid NFL week in %d" % year)
    if data.duplicated(["season", "week", "player_id"]).any():
        raise ValueError("Duplicate player/week rows in %d" % year)
    return data, {
        "season": year, "rows": int(len(data)),
        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "source": source, "status": "validated",
    }

def prior_game_features(frame):
    frame = frame.sort_values(["player_id", "season", "week"]).copy()
    groups = frame.groupby("player_id", sort=False)
    # All features refer to observations strictly prior to the target week.
    frame["prior_observations"] = groups.cumcount()
    # Prior observed roster position, never the target-week position.
    frame["prior_position"] = groups["position"].transform(
        lambda s: s.ffill().shift(1)
    )
    for key in MEASURES:
        frame[key] = pd.to_numeric(frame[key], errors="coerce")
        frame["prior5_" + key] = frame.groupby("player_id", sort=False)[key].transform(
            lambda s: s.shift(1).rolling(5, min_periods=1).mean()
        )
        frame["prior3_" + key] = frame.groupby("player_id", sort=False)[key].transform(
            lambda s: s.shift(1).rolling(3, min_periods=1).mean()
        )
    return frame[["player_id", "season", "week", "prior_position",
                  "prior_observations"] + list(MEASURES)
                 + ["prior5_" + k for k in MEASURES]
                 + ["prior3_" + k for k in MEASURES]]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seasons", type=int, nargs="+", required=True)
    parser.add_argument("--output", default="output")
    args = parser.parse_args()
    folder = Path(args.output)
    folder.mkdir(parents=True, exist_ok=True)
    frames, records = [], []
    for year in args.seasons:
        frame, record = download(year, folder)
        frames.append(frame)
        records.append(record)
    raw = pd.concat(frames, ignore_index=True)
    unidentified = raw["player_id"].isna() | raw["player_id"].astype("string").str.strip().fillna("").eq("")
    excluded = int(unidentified.sum())
    identified = raw.loc[~unidentified].copy()
    if identified.empty:
        raise ValueError("No identified player-week records after quarantine")
    if identified.duplicated(["season", "week", "player_id"]).any():
        raise ValueError("Duplicate identified player-week rows")
    features = prior_game_features(identified)
    features.to_csv(folder / "features.csv", index=False)
    manifest = {
        "status": "historical_data_validated",
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "seasons": records,
        "player_week_rows": int(sum(r["rows"] for r in records)),
        "feature_rows": int(len(features)),
        "unidentified_player_week_rows_quarantined": excluded,
        "player_identity_verified_externally": False,
        "verified_prop_prices": False, "calibrated_probabilities": False,
        "backtested_roi": False,
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))

if __name__ == "__main__":
    main()
