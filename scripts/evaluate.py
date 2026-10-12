"""Chronological player-stat forecasting baseline; NOT a betting/ROI backtest.

Training years: 2021-2023. Model selection: 2024 only.
Final held-out evaluation: 2025. No sportsbook prices are used.
Important limitation: nflverse player-week rows reflect postgame participants,
not a historical pregame-eligible player universe.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error

METRICS = ("receptions", "receiving_yards", "rushing_yards", "passing_yards")
FEATURES = ["prior5_" + m for m in METRICS]
PARAMETERS = [1.0, 10.0, 100.0]

def evaluate(df):
    missing = set(["season", "week", "player_id"] + list(METRICS) + FEATURES) - set(df.columns)
    if missing:
        raise ValueError("Missing historical features: " + str(sorted(missing)))
    df = df.copy()
    df["prior_observations"] = df.groupby("player_id", sort=False).cumcount()
    df = df[df.prior_observations >= 3]
    for c in FEATURES + list(METRICS):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    records = []
    for market in METRICS:
        eligible = df[df[market].notna() & df["prior5_" + market].notna()]
        training = eligible[eligible.season.between(2021, 2023)]
        validation = eligible[eligible.season.eq(2024)]
        testing = eligible[eligible.season.eq(2025)]
        if min(len(training), len(validation), len(testing)) < 25:
            raise ValueError("Insufficient samples in chronological splits for " + market)
        chosen = None
        for alpha in PARAMETERS:
            pipeline = make_pipeline(SimpleImputer(strategy="constant", fill_value=0),
                                     StandardScaler(), Ridge(alpha=alpha))
            pipeline.fit(training[FEATURES], training[market])
            p = np.maximum(pipeline.predict(validation[FEATURES]), 0)
            mae = float(mean_absolute_error(validation[market], p))
            if chosen is None or mae < chosen[0]:
                chosen = (mae, alpha)
        model = make_pipeline(SimpleImputer(strategy="constant", fill_value=0),
                              StandardScaler(), Ridge(alpha=chosen[1]))
        model.fit(pd.concat([training[FEATURES], validation[FEATURES]]),
                  pd.concat([training[market], validation[market]]))
        truth = testing[market].to_numpy()
        predicted = np.maximum(model.predict(testing[FEATURES]), 0)
        baseline = testing["prior5_" + market].to_numpy()
        a = float(mean_absolute_error(truth, predicted))
        b = float(mean_absolute_error(truth, baseline))
        records.append({
            "market": market, "train_n": int(len(training)), "validation_n": int(len(validation)),
            "test_n": int(len(testing)), "model":"ridge_lagged_stats",
            "selected_alpha_on_2024": chosen[1],
            "test_2025_model_mae": round(a, 4),
            "test_2025_recent5_mae": round(b, 4),
            "test_2025_model_rmse": round(float(np.sqrt(mean_squared_error(truth, predicted))), 4),
            "test_2025_baseline_rmse": round(float(np.sqrt(mean_squared_error(truth, baseline))), 4),
            "mae_gain_vs_recent5_pct": round(100*(b-a)/b,2) if b>0 else None,
            "wins_mae_vs_baseline": bool(a < b),
        })
    return {
        "status": "heldout_player_stats_evaluation",
        "created_at_utc":datetime.now(timezone.utc).isoformat(),
        "train_years":[2021,2022,2023], "validation_year":2024,"test_year":2025,
        "evaluated_on":"observed player-week records with >=3 prior entries",
        "pregame_eligible_universe_verified":False,
        "bookmaker_odds_available":False,"true_hit_probability_calibrated":False,
        "roi_backtest_complete":False,
        "markets": records,
    }

if __name__ == "__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--features",default="output/features.csv")
    ap.add_argument("--output",default="output/evaluation.json")
    args=ap.parse_args()
    report=evaluate(pd.read_csv(args.features))
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
