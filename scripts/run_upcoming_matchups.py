"""Generate an auditable baseline slate forecast from public nflverse schedule."""
import argparse
from pathlib import Path
import pandas as pd
from matchup_engine.upcoming import upcoming_board
from matchup_engine.quality import validate_prediction_board

SOURCE="https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--as-of",required=True,help="YYYY-MM-DD cutoff (schedule local date)")
    parser.add_argument("--output",default="artifacts/matchup/upcoming_predictions.csv")
    args=parser.parse_args()
    schedule=pd.read_csv(SOURCE)
    board=upcoming_board(schedule,args.as_of)
    quality=validate_prediction_board(board,schedule,args.as_of)
    print('Quality checks passed:',quality)
    output=Path(args.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    board.to_csv(output,index=False)
    print(board.to_string(index=False))

if __name__=="__main__":
    main()
