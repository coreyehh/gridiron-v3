"""Expanding-season evaluation: train only on earlier seasons."""
import pandas as pd
from sklearn.metrics import brier_score_loss, mean_absolute_error, log_loss
from .predict import fit_baseline, predict

def walk_forward(frame, min_train_games=100):
    predictions = []
    for season in sorted(frame.season.unique()):
        train = frame[frame.season < season]
        test = frame[frame.season == season]
        if len(train) < min_train_games or test.empty:
            continue
        models = fit_baseline(train)
        p = predict(models,test)
        p["season"] = season
        p["actual_margin"] = test.margin.to_numpy()
        p["actual_total"] = test.total.to_numpy()
        p["actual_home_win"] = test.home_win.to_numpy()
        predictions.append(p)
    if not predictions:
        raise ValueError("Not enough historical seasons for out-of-sample evaluation")
    out = pd.concat(predictions,ignore_index=True)
    metrics = {
        "games":len(out),
        "brier":brier_score_loss(out.actual_home_win,out.home_win_probability),
        "log_loss":log_loss(out.actual_home_win,out.home_win_probability,labels=[0,1]),
        "margin_mae":mean_absolute_error(out.actual_margin,out.pred_margin),
        "total_mae":mean_absolute_error(out.actual_total,out.pred_total),
    }
    return out,metrics
