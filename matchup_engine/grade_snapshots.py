"""Grade immutable pregame matchup forecasts against completed NFL results."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

def grade_prediction_snapshot(snapshot_csv, metadata_json, results, through_date=None):
    raw=Path(snapshot_csv).read_bytes()
    metadata=json.loads(Path(metadata_json).read_text())
    if hashlib.sha256(raw).hexdigest()!=metadata["sha256"]:
        raise ValueError("Snapshot integrity verification failed")
    forecasts=pd.read_csv(snapshot_csv)
    # The schedule only supplies calendar dates, not verified kickoff times.
    # Conservatively refuse same-day snapshots: pregame status cannot be proven.
    snapshot_time=pd.Timestamp(metadata["generated_at_utc"])
    if snapshot_time.tzinfo is None:
        raise ValueError("Snapshot timestamp must include a timezone")
    if pd.Timestamp(metadata["as_of"]).date()>snapshot_time.date():
        raise ValueError("Snapshot cutoff is later than generation date")
    required={"game_id","gameday","home_team","away_team","home_win_probability",
              "projected_home_points","projected_away_points","fair_home_spread","pred_total"}
    if required-set(forecasts.columns):
        raise ValueError("Snapshot missing required forecast fields")
    if (pd.to_datetime(forecasts.gameday).dt.date<=snapshot_time.date()).any():
        raise ValueError("Snapshot not provably pregame: game date is not after generation date")
    if forecasts.game_id.duplicated().any():
        raise ValueError("Duplicate game IDs in snapshot")
    if results.game_id.duplicated().any():
        raise ValueError("Duplicate game IDs in results")
    actual=results[["game_id","home_team","away_team","home_score","away_score","gameday"]].copy()
    actual=actual.rename(columns={"home_team":"actual_home_team","away_team":"actual_away_team",
                                   "gameday":"actual_gameday"})
    if through_date is not None:
        actual=actual.loc[pd.to_datetime(actual.actual_gameday)<=pd.Timestamp(through_date)]
    joined=forecasts.merge(actual,on="game_id",how="left",validate="one_to_one")
    if ((joined.actual_home_team.notna())&
        ((joined.home_team!=joined.actual_home_team)|
         (joined.away_team!=joined.actual_away_team))).any():
        raise ValueError("Team mismatch between snapshot and results")
    eligible=joined.home_score.notna()&joined.away_score.notna()
    completed=joined.loc[eligible].copy()
    # NFL regular-season ties are neither home wins nor away wins.
    ties=completed.home_score.eq(completed.away_score)
    completed["actual_home_win"]=(completed.home_score>completed.away_score).astype(float)
    completed["actual_margin"]=completed.home_score-completed.away_score
    completed["actual_total"]=completed.home_score+completed.away_score
    completed["winner_correct"]=((completed.home_win_probability>=.5)==
                                  (completed.actual_home_win==1)).astype(float)
    completed.loc[ties,["winner_correct","actual_home_win"]]=float("nan")
    completed["brier_error"]=(completed.home_win_probability-completed.actual_home_win)**2
    p=completed.home_win_probability.clip(1e-9,1-1e-9)
    completed["log_loss"]=-(completed.actual_home_win*np.log(p)+
                             (1-completed.actual_home_win)*np.log(1-p))
    completed["margin_absolute_error"]=(completed.actual_margin+
                                         completed.fair_home_spread).abs()
    completed["total_absolute_error"]=(completed.actual_total-completed.pred_total).abs()
    metrics={"snapshot_games":int(len(forecasts)),"graded_games":int(len(completed)),
             "pending_games":int(len(forecasts)-len(completed))}
    for name,column in [("winner_accuracy","winner_correct"),("brier","brier_error"),
                        ("log_loss","log_loss"),("margin_mae","margin_absolute_error"),
                        ("total_mae","total_absolute_error")]:
        metrics[name]=float(completed[column].mean()) if len(completed) else None
    return completed,metrics
