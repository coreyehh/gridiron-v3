"""Position-aware *proxy* prop evaluation with pregame-history-only selection.

WARNING: official nflverse player-stat rows are observed postgame rows.
Historical full active/rostered player universe is not yet ingested.
Eligibility is a prior-usage proxy, NOT verified bookmaker market availability.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

CONFIG = [
    ("QB", "passing_yards", 100.0),
    ("RB", "rushing_yards", 15.0),
    ("RB", "receptions", 0.75),
    ("RB", "receiving_yards", 7.5),
    ("WR", "receptions", 1.5),
    ("WR", "receiving_yards", 20.0),
    ("TE", "receptions", 1.0),
    ("TE", "receiving_yards", 10.0),
]
FEATURES = ["prior5_receptions", "prior5_receiving_yards",
            "prior5_rushing_yards", "prior5_passing_yards",
            "prior3_receptions", "prior3_receiving_yards",
            "prior3_rushing_yards", "prior3_passing_yards"]
ALPHAS = (1.0, 10.0, 100.0)

def prepare(frame):
    needed = set(["season", "week", "player_id", "prior_position", "prior_observations"] + FEATURES +
                 ["receptions", "receiving_yards", "rushing_yards", "passing_yards"])
    missing = needed - set(frame.columns)
    if missing:
        raise ValueError("Missing features: "+", ".join(sorted(missing)))
    frame = frame.copy()
    for c in FEATURES + ["receptions", "receiving_yards", "rushing_yards", "passing_yards"]:
        frame[c] = pd.to_numeric(frame[c], errors="coerce")
    frame["prior_position"] = frame["prior_position"].astype(str).str.upper()
    return frame

def evaluate(frame):
    frame = prepare(frame)
    outcomes = []
    for position, market, threshold in CONFIG:
        # The selection uses only lagged, pregame values, never this week's yards/catches.
        market_prev = "prior5_" + market
        pool = frame[(frame.prior_position == position) &
                     (frame.prior_observations >= 3) &
                     (frame[market_prev] >= threshold) &
                     frame[market].notna()].copy()
        train = pool[pool.season.between(2021, 2023)]
        val = pool[pool.season == 2024]
        test = pool[pool.season == 2025]
        row = {"position": position, "market": market, "prior5_eligibility_threshold": threshold,
               "train_n": int(len(train)), "validation_n": int(len(val)), "test_n": int(len(test))}
        if min(len(train), len(val), len(test)) < 50:
            outcomes.append(dict(row, status="insufficient_samples"))
            continue
        selected = None
        for alpha in ALPHAS:
            model = make_pipeline(SimpleImputer(strategy="constant", fill_value=0),
                                  StandardScaler(), Ridge(alpha=alpha))
            model.fit(train[FEATURES], train[market])
            pred = np.maximum(model.predict(val[FEATURES]), 0)
            score = mean_absolute_error(val[market], pred)
            if selected is None or score < selected[0]:
                selected = (score, alpha)
        final = make_pipeline(SimpleImputer(strategy="constant", fill_value=0),
                              StandardScaler(), Ridge(alpha=selected[1]))
        tv = pd.concat([train, val], ignore_index=True)
        final.fit(tv[FEATURES], tv[market])
        observed = test[market].to_numpy()
        model_prediction = np.maximum(final.predict(test[FEATURES]), 0)
        benchmark = test[market_prev].to_numpy()
        mae_model = mean_absolute_error(observed, model_prediction)
        mae_benchmark = mean_absolute_error(observed, benchmark)
        outcomes.append(dict(row, status="evaluated", alpha=selected[1],
                             model_mae=round(float(mae_model), 3),
                             recent5_mae=round(float(mae_benchmark), 3),
                             model_rmse=round(float(np.sqrt(mean_squared_error(observed, model_prediction))), 3),
                             recent5_rmse=round(float(np.sqrt(mean_squared_error(observed, benchmark))), 3),
                             mae_improvement_pct=round(float(100*(mae_benchmark-mae_model)/mae_benchmark), 2) if mae_benchmark else None,
                             improved=bool(mae_model < mae_benchmark)))
    return {
        "status": "position_aware_pregame_usage_proxy_evaluation",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "training_seasons": [2021, 2022, 2023],
        "validation_season": 2024, "heldout_season": 2025,
        "eligibility": "Prior 5-game production and prior observed position; postgame-record universe still creates survivorship bias",
        "limitations": [
            "Not historical bookmaker-offered prop markets",
            "Missing pregame roster/active eligibility for zero-stat or inactive players",
            "No sportsbook odds, opponent scheme, injuries, routes or weather",
            "Current-week production never used in feature or threshold selection"
        ],
        "bookmaker_prices_available": False, "roi_calculated": False,
        "calibrated_probabilities": False, "results": outcomes
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--features", default="output/features.csv")
    p.add_argument("--output", default="output/position_evaluation.json")
    args = p.parse_args()
    result = evaluate(pd.read_csv(args.features))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
