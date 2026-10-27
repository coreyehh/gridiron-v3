"""Verify player-week box results against a pinned nflverse parquet artifact.

The expected SHA256 must be supplied independently from the observation rows.
This proves agreement with pinned bytes, not official NFL attestation or
fixture identity; callers must supply a separately trusted fixture/week map.
"""
import hashlib,math
from pathlib import Path
import pandas as pd

MARKETS={"passing_yards":"passing_yards","pass_attempts":"attempts",
 "completions":"completions","interceptions":"passing_interceptions",
 "passing_touchdowns":"passing_tds","rushing_yards":"rushing_yards",
 "rush_attempts":"carries","receptions":"receptions",
 "receiving_yards":"receiving_yards","rushing_touchdowns":"rushing_tds",
 "receiving_touchdowns":"receiving_tds"}

class PinnedNflverseResultVerifier:
    def __init__(self, parquet_path, *, expected_sha256, fixture_weeks):
        data=Path(parquet_path).read_bytes()
        if not expected_sha256 or hashlib.sha256(data).hexdigest()!=expected_sha256:
            raise ValueError("Nflverse artifact hash mismatch")
        self.source_sha256=expected_sha256
        self.fixture_weeks=dict(fixture_weeks)
        frame=pd.read_parquet(parquet_path)
        required={"season","week","player_id"}
        if not required.issubset(frame.columns):
            raise ValueError("Missing nflverse identity fields")
        identified=frame["player_id"].notna() & frame["player_id"].astype("string").str.strip().fillna("").ne("")
        frame=frame.loc[identified].copy()
        if frame.duplicated(["season","week","player_id"]).any():
            raise ValueError("Duplicate nflverse player-week")
        self.lookup={(int(r.season),int(r.week),str(r.player_id)):r
                     for r in frame.itertuples(index=False)}
    def verify(self, observation):
        try:
            fixture=str(observation["fixture_id"])
            season,week=self.fixture_weeks[fixture]
            market=str(observation["market"])
            if market not in MARKETS:return False
            row=self.lookup.get((int(season),int(week),str(observation["player_id"])))
            if row is None:return False
            column=MARKETS[market]
            if column=="passing_interceptions" and not hasattr(row,column):
                column="interceptions"
            if not hasattr(row,column):return False
            actual=float(observation["actual"])
            source=float(getattr(row,column))
            return (math.isfinite(source) and math.isfinite(actual) and actual>=0
                    and source==actual
                    and observation.get("source_name")=="nflverse_player_week"
                    and observation.get("source_record_id")==f"{season}-{week}-{observation['player_id']}"
                    and observation.get("source_sha256")==self.source_sha256)
        except (KeyError,TypeError,ValueError,OverflowError):
            return False
