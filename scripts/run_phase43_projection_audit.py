"""Audit saved Phase43 snapshot and result-file readiness before scoring.

No historical snapshots are reconstructed. An existing file's internal digest
is validated, but provenance outside the repository is not independently proven.
"""
import argparse,json
from pathlib import Path
from scripts.phase43_projection_ledger_export import export
from scripts.phase43_projection_error_report import evaluate
from scripts.result_source_verifier import verify_results

def run(snapshot_path,observations_path,*,min_sample=10,verifier=None):
    snapshot=json.loads(Path(snapshot_path).read_text())
    original=export(snapshot)
    observations=json.loads(Path(observations_path).read_text())
    if not isinstance(observations,list):raise ValueError("Expected observations array")
    verified=verify_results(observations,verifier=verifier)
    result=evaluate(original,verified,min_sample=min_sample)
    result["source_snapshot_path"]=str(snapshot_path)
    result["source_observations_path"]=str(observations_path)
    result["snapshot_digest"]=original["snapshot_sha256"]
    result["snapshot_external_provenance_verified"]=False
    result["real_world_betting_edge_certified"]=False
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--snapshot",required=True)
    p.add_argument("--observations",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--min-sample",type=int,default=10)
    args=p.parse_args()
    result=run(args.snapshot,args.observations,min_sample=args.min_sample)
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"markets":list(result["markets"]),"unmatched":result["unmatched_projection_count"],
                      "external_provenance_verified":False}))
if __name__=="__main__":main()
