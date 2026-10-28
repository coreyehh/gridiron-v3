"""Execute the receiving threshold diagnostic on source-tracked 2025/2026 nflverse boxes."""
import argparse,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
from scripts.ingest import download
from scripts.phase43_receiving_threshold_walkforward import evaluate

def run(folder,first_week=4,last_week=8,min_samples=8,min_prior_receptions=None):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    frames=[];sources={}
    for year in (2025,2026):
        data,meta=download(year,folder)
        frames.append(data)
        sources[str(year)]={"sha256":meta["sha256"],"rows":meta["rows"],"source":meta["source"]}
    raw=pd.concat(frames,ignore_index=True)
    observed=raw[(raw.season==2026)&(raw.week>=first_week)]
    if observed.empty:raise ValueError("No 2026 evaluation observations")
    available=int(observed.week.max())
    end=min(last_week,available)
    if end<first_week:raise ValueError("No completed evaluation window")
    report=evaluate(raw,first_week=first_week,last_week=end,min_samples=min_samples,min_prior_receptions=min_prior_receptions)
    report["source_manifest"]=sources
    report["generated_at_utc"]=datetime.now(timezone.utc).isoformat()
    report["requested_last_week"]=last_week
    report["actual_last_week"]=end
    report["verified_market_prices"]=False
    report["approved_wagers"]=0
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--first-week",type=int,default=4)
    p.add_argument("--last-week",type=int,default=8)
    p.add_argument("--min-samples",type=int,default=8)
    p.add_argument("--min-prior-receptions",type=float,default=None)
    p.add_argument("--data-dir",default="private_data")
    p.add_argument("--output",default="output/phase43_receiving_threshold_evaluation.json")
    a=p.parse_args()
    result=run(a.data_dir,a.first_week,a.last_week,a.min_samples,a.min_prior_receptions)
    dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"scored_records":result["scored_records"],
       "actual_last_week":result["actual_last_week"],
       "approved_wagers":0,"output":str(dest)}))
if __name__=="__main__":main()
