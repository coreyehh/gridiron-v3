"""Verify and grade a saved GRIDIRON forecast snapshot."""
import argparse
import json
from pathlib import Path
import pandas as pd
from matchup_engine.grade_snapshots import grade_prediction_snapshot
from matchup_engine.paired_accountability import compare_scenario_errors
from matchup_engine.ledger import append_grading_ledger, verify_grading_ledger
from matchup_engine.ingest import SOURCE

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--snapshot",required=True)
    parser.add_argument("--metadata",required=True)
    parser.add_argument("--through-date")
    parser.add_argument("--ledger-dir",help="Optional persistent append-only ledger directory")
    parser.add_argument("--output",default="artifacts/matchup/graded_predictions.csv")
    args=parser.parse_args()
    results=pd.read_csv(SOURCE)
    graded,metrics=grade_prediction_snapshot(args.snapshot,args.metadata,results,args.through_date)
    output=Path(args.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    graded.to_csv(output,index=False)
    if "scenario_home_points" in graded.columns:
        paired,paired_metrics=compare_scenario_errors(graded)
        paired.to_csv(output.with_suffix(".paired.csv"),index=False)
        metrics["personnel_comparison"]=paired_metrics
    output.with_suffix(".metrics.json").write_text(json.dumps(metrics,indent=2))
    if args.ledger_dir:
        snapshot_hash=json.loads(Path(args.metadata).read_text())["sha256"]
        entry=append_grading_ledger(graded,metrics,args.ledger_dir,snapshot_hash)
        print("Ledger entry:",entry["grades_file"])
        print("Ledger integrity:",verify_grading_ledger(args.ledger_dir))
    print(json.dumps(metrics,indent=2))

if __name__=="__main__":
    main()
