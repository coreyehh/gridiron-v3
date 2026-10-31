"""Phase 48 historical out-of-sample baseline runner."""
import argparse
import json
from pathlib import Path
from matchup_engine.ingest import fetch_completed_games
from matchup_engine.features import make_training_frame
from matchup_engine.backtest import walk_forward

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--through-season",type=int,default=2025)
    parser.add_argument("--output-dir",default="artifacts/matchup")
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True,exist_ok=True)
    games = fetch_completed_games(through_season=args.through_season)
    frame = make_training_frame(games)
    predictions, metrics = walk_forward(frame)
    predictions.to_csv(output/"out_of_sample_predictions.csv",index=False)
    (output/"metrics.json").write_text(json.dumps(metrics,indent=2)+"\n")
    print(json.dumps(metrics,indent=2))

if __name__ == "__main__":
    main()
