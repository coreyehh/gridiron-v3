"""Fail closed on stale or inconsistent weekly forecast inputs."""
import pandas as pd

def validate_prediction_board(board, schedule, as_of, max_schedule_age_days=7):
    if board.empty:
        raise ValueError("Empty prediction board")
    if board.game_id.duplicated().any():
        raise ValueError("Duplicate game IDs")
    if board[["home_win_probability","away_win_probability","projected_home_points",
              "projected_away_points","pred_total","fair_home_spread"]].isna().any().any():
        raise ValueError("Missing forecast values")
    p=board.home_win_probability
    q=board.away_win_probability
    if not (p.between(0,1).all() and q.between(0,1).all() and ((p+q-1).abs()<1e-6).all()):
        raise ValueError("Invalid win probabilities")
    if not ((board.projected_home_points+board.projected_away_points-board.pred_total).abs()<1e-6).all():
        raise ValueError("Inconsistent projected totals")
    if not ((board.projected_away_points-board.projected_home_points-board.fair_home_spread).abs()<1e-6).all():
        raise ValueError("Inconsistent fair spreads")
    if board.week.nunique()!=1 or board.season.nunique()!=1:
        raise ValueError("Forecast includes multiple weeks or seasons")
    dates=pd.to_datetime(board.gameday)
    if (dates<pd.Timestamp(as_of)).any():
        raise ValueError("Forecast includes past games")
    # Do not silently accept a schedule that has no recent completed results.
    schedule=schedule.copy()
    schedule["gameday"]=pd.to_datetime(schedule.gameday)
    completed=schedule.loc[(schedule.gameday<pd.Timestamp(as_of))&
                           schedule.home_score.notna()&schedule.away_score.notna()]
    if completed.empty or (pd.Timestamp(as_of)-completed.gameday.max()).days>max_schedule_age_days:
        raise ValueError("Schedule/results appear stale")
    return {"games":len(board),"season":int(board.season.iloc[0]),
            "week":int(board.week.iloc[0]),"latest_completed_game":str(completed.gameday.max().date())}
