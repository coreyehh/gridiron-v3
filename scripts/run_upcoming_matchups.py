"""Generate an auditable baseline slate forecast from public nflverse schedule."""
import argparse
from pathlib import Path
import pandas as pd
from matchup_engine.upcoming import upcoming_board
from matchup_engine.quality import validate_prediction_board
from matchup_engine.personnel import apply_personnel_scenarios
from matchup_engine.personnel_evidence import audit_personnel_evidence
from matchup_engine.snapshots import save_prediction_snapshot

SOURCE="https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--as-of",required=True,help="YYYY-MM-DD cutoff (schedule local date)")
    parser.add_argument("--personnel-csv",help="Optional sourced, timestamped manual personnel scenario adjustments")
    parser.add_argument("--output",default="artifacts/matchup/upcoming_predictions.csv")
    args=parser.parse_args()
    schedule=pd.read_csv(SOURCE)
    board=upcoming_board(schedule,args.as_of)
    quality=validate_prediction_board(board,schedule,args.as_of)
    if args.personnel_csv:
        adjustments=pd.read_csv(args.personnel_csv)
        audit_personnel_evidence(adjustments,args.as_of)
        board=apply_personnel_scenarios(board,adjustments,args.as_of)
    print('Quality checks passed:',quality)
    output=Path(args.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    board.to_csv(output,index=False)
    snapshot_csv,snapshot_metadata=save_prediction_snapshot(board,output.parent/'snapshots',args.as_of)
    print('Accountability snapshot:',snapshot_csv,snapshot_metadata)
    print(board.to_string(index=False))

if __name__=="__main__":
    main()
