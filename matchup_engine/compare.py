"""Fair, paired out-of-sample comparison on identical historical games."""
import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss,log_loss,mean_absolute_error
from .features import FEATURES
from .epa_features import EPA_FEATURES
from .predict import fit_baseline,predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge,LogisticRegression

def _fit(train,columns):
    X=train[columns]
    return {
        "margin":make_pipeline(StandardScaler(),Ridge(alpha=10)).fit(X,train.margin),
        "total":make_pipeline(StandardScaler(),Ridge(alpha=10)).fit(X,train.total),
        "winner":make_pipeline(StandardScaler(),LogisticRegression(C=0.2,max_iter=1000)).fit(X,train.home_win),
    }

def _predict(models,frame,columns):
    X=frame[columns]
    return pd.DataFrame({
        "game_id":frame.game_id.to_numpy(),
        "season":frame.season.to_numpy(),
        "actual_home_win":frame.home_win.to_numpy(),
        "actual_margin":frame.margin.to_numpy(),
        "actual_total":frame.total.to_numpy(),
        "home_win_probability":models["winner"].predict_proba(X)[:,1],
        "pred_margin":models["margin"].predict(X),
        "pred_total":models["total"].predict(X),
    })

def _metrics(p):
    return {
        "games":int(len(p)),
        "brier":float(brier_score_loss(p.actual_home_win,p.home_win_probability)),
        "log_loss":float(log_loss(p.actual_home_win,p.home_win_probability,labels=[0,1])),
        "margin_mae":float(mean_absolute_error(p.actual_margin,p.pred_margin)),
        "total_mae":float(mean_absolute_error(p.actual_total,p.pred_total)),
    }

def compare_models(frame,min_train_games=100):
    """Both models train/evaluate on identical EPA-complete game rows."""
    required=FEATURES+EPA_FEATURES
    data=frame.dropna(subset=required).sort_values(["gameday","game_id"])
    output={"baseline":[],"epa":[]}
    for season in sorted(data.season.unique()):
        train=data.loc[data.season < season]
        test=data.loc[data.season == season]
        if len(train)<min_train_games or test.empty or train.home_win.nunique()<2:
            continue
        for name,cols in (("baseline",FEATURES),("epa",FEATURES+EPA_FEATURES)):
            output[name].append(_predict(_fit(train,cols),test,cols))
    if not output["baseline"]:
        raise ValueError("Insufficient EPA-complete seasons for paired comparison")
    predictions={name:pd.concat(parts,ignore_index=True) for name,parts in output.items()}
    if not predictions["baseline"].game_id.equals(predictions["epa"].game_id):
        raise AssertionError("Paired test games do not match")
    return predictions,{name:_metrics(p) for name,p in predictions.items()}
