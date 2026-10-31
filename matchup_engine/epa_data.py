"""Load historical nflverse play-by-play data for opponent-adjusted EPA."""
from pathlib import Path
import pandas as pd
from .epa_ratings import aggregate_games

URL = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{season}.parquet"

def load_epa_games(seasons, cache_dir="data/matchup/pbp"):
    cache = Path(cache_dir)
    cache.mkdir(parents=True,exist_ok=True)
    all_games = []
    for season in seasons:
        path=cache / f"play_by_play_{season}.parquet"
        if not path.exists():
            df=pd.read_parquet(URL.format(season=season),
                columns=["game_id","game_date","posteam","defteam","play_type","epa"])
            df.to_parquet(path,index=False)
        else:
            df=pd.read_parquet(path,columns=["game_id","game_date","posteam","defteam","play_type","epa"])
        all_games.append(aggregate_games(df))
    if not all_games:
        raise ValueError("At least one season required")
    return pd.concat(all_games,ignore_index=True)
