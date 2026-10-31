"""Read validated historical NFL game-level input. No network side effects."""
import pandas as pd

REQUIRED = {"season", "week", "gameday", "game_id", "home_team", "away_team", "home_score", "away_score"}

def load_games(path):
    df = pd.read_csv(path)
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if df.game_id.isna().any() or df.game_id.duplicated().any():
        raise ValueError("game_id must be non-null and unique")
    df["gameday"] = pd.to_datetime(df["gameday"], errors="raise")
    for col in ("home_score", "away_score"):
        df[col] = pd.to_numeric(df[col], errors="raise")
    if df[["home_score", "away_score"]].isna().any().any():
        raise ValueError("Completed historical games require scores")
    return df.sort_values(["gameday", "game_id"]).reset_index(drop=True)
