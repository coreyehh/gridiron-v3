"""Simple baseline, deliberately not marketed as a validated betting model."""
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge, LogisticRegression
from .features import FEATURES

def fit_baseline(train):
    if len(train) < 30 or train.home_win.nunique() < 2:
        raise ValueError("At least 30 games and both win classes required")
    X = train[FEATURES]
    margin = make_pipeline(StandardScaler(),Ridge(alpha=10)).fit(X,train.margin)
    total = make_pipeline(StandardScaler(),Ridge(alpha=10)).fit(X,train.total)
    winner = make_pipeline(StandardScaler(),LogisticRegression(C=0.2,max_iter=1000)).fit(X,train.home_win)
    return {"margin":margin,"total":total,"winner":winner}

def predict(models, frame):
    out = frame[["game_id","gameday","home_team","away_team"]].copy()
    out["pred_margin"] = models["margin"].predict(frame[FEATURES])
    out["pred_total"] = models["total"].predict(frame[FEATURES])
    out["home_win_probability"] = models["winner"].predict_proba(frame[FEATURES])[:,1]
    out["pred_home_points"] = (out.pred_total+out.pred_margin)/2
    out["pred_away_points"] = (out.pred_total-out.pred_margin)/2
    return out
