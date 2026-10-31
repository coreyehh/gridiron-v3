"""Simple out-of-sample reference forecasts for the matchup engine."""
import numpy as np
from sklearn.metrics import brier_score_loss, mean_absolute_error, log_loss

def evaluate_reference(predictions, home_win_probability=0.5, margin=0.0, total=None):
    """Reference forecasts are fixed, not estimated using the test period."""
    y = predictions.actual_home_win.to_numpy()
    n = len(predictions)
    if total is None:
        raise ValueError("Provide a predeclared total benchmark; never derive it from test results")
    p = np.full(n, home_win_probability)
    return {
        "games":n,
        "brier":float(brier_score_loss(y,p)),
        "log_loss":float(log_loss(y,p,labels=[0,1])),
        "margin_mae":float(mean_absolute_error(predictions.actual_margin,np.full(n,margin))),
        "total_mae":float(mean_absolute_error(predictions.actual_total,np.full(n,total))),
    }
