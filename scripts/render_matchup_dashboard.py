"""Render static HTML from a saved GRIDIRON prediction CSV."""
import argparse
import json
from pathlib import Path
import pandas as pd
from matchup_engine.dashboard import write_matchup_dashboard

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--predictions",required=True)
    parser.add_argument("--metrics",help="Optional grading metrics JSON")
    parser.add_argument("--output",default="artifacts/matchup/dashboard.html")
    args=parser.parse_args()
    board=pd.read_csv(args.predictions)
    metrics=json.loads(Path(args.metrics).read_text()) if args.metrics else None
    print("Dashboard:",write_matchup_dashboard(board,args.output,metrics))

if __name__=="__main__":
    main()
