"""Verify and grade a saved GRIDIRON forecast snapshot."""
import argparse
import json
from pathlib import Path
import pandas as pd
from matchup_engine.grade_snapshots import grade_prediction_snapshot
from matchup_engine.ingest import SOURCE

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--snapshot",required=True)
    parser.add_argument("--metadata",required=True)
    parser.add_argument("--through-date")
    parser.add_argument("--output",default="artifacts/matchup/graded_predictions.csv")
    args=parser.parse_args()
    results=pd.read_csv(SOURCE)
    graded,metrics=grade_prediction_snapshot(args.snapshot,args.metadata,results,args.through_date)
    output=Path(args.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    graded.to_csv(output,index=False)
    output.with_suffix(".metrics.json").write_text(json.dumps(metrics,indent=2))
    print(json.dumps(metrics,indent=2))

if __name__=="__main__":
    main()
