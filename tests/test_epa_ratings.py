import pandas as pd
from matchup_engine.epa_ratings import aggregate_games, adjusted_team_ratings

def test_no_future_games_in_ratings():
    rows=[]
    for i in range(5):
        for play_type in ("pass","run"):
            rows.append(dict(game_id=f"old{i}",game_date="2025-09-01",
                posteam="A",defteam="B",play_type=play_type,epa=0.1))
            rows.append(dict(game_id=f"old{i}",game_date="2025-09-01",
                posteam="B",defteam="A",play_type=play_type,epa=-0.1))
    plays=pd.DataFrame(rows)
    before=adjusted_team_ratings(aggregate_games(plays),"2025-09-02")
    future=pd.DataFrame([dict(game_id="future",game_date="2025-09-03",
        posteam="A",defteam="B",play_type="pass",epa=100)])
    after=adjusted_team_ratings(aggregate_games(pd.concat([plays,future],ignore_index=True)),"2025-09-02")
    pd.testing.assert_frame_equal(before,after)

def test_same_day_games_excluded():
    p=pd.DataFrame([dict(game_id=f"g{i}",game_date="2025-09-02",
        posteam="A",defteam="B",play_type="pass",epa=1) for i in range(5)])
    assert adjusted_team_ratings(aggregate_games(p),"2025-09-02").empty
