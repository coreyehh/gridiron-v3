import pandas as pd
from matchup_engine.epa_features import add_epa_features, EPA_FEATURES
from matchup_engine.epa_ratings import aggregate_games

def test_future_epa_does_not_affect_pregame_features():
    plays=[]
    for i in range(5):
        for offense,defense,epa in (("A","B",0.2),("B","A",-0.1)):
            for kind in ("pass","run"):
                plays.append(dict(game_id=f"old{i}",game_date="2025-09-01",
                    posteam=offense,defteam=defense,play_type=kind,epa=epa))
    base=pd.DataFrame(plays)
    frame=pd.DataFrame([dict(game_id="target",gameday=pd.Timestamp("2025-09-08"),
        home_team="A",away_team="B")])
    a=add_epa_features(frame,aggregate_games(base))
    future=pd.DataFrame([dict(game_id="future",game_date="2025-09-09",
        posteam="A",defteam="B",play_type="pass",epa=999)])
    b=add_epa_features(frame,aggregate_games(pd.concat([base,future],ignore_index=True)))
    pd.testing.assert_frame_equal(a[EPA_FEATURES],b[EPA_FEATURES])
