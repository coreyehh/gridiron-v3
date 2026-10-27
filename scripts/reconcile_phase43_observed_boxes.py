"""Reconcile original Phase43 point projections with pinned completed player-week boxes.

Only source-backed observed player rows are scored. Missing rows are not zeros.
The generated evidence is tied to the caller's pinned schedule and stats hashes.
"""
import argparse,json
import pandas as pd
from pathlib import Path
from scripts.phase43_projection_ledger_export import export
from scripts.phase43_projection_error_report import evaluate
from scripts.pinned_fixture_mapper import fixture_weeks
from scripts.nflverse_result_verifier import PinnedNflverseResultVerifier,MARKETS
from scripts.result_source_verifier import verify_results

def reconcile(snapshot, *, schedule_path,schedule_sha256,stats_path,stats_sha256,min_sample=10):
    original=export(snapshot)
    mapping=fixture_weeks(schedule_path,expected_sha256=schedule_sha256)
    verifier=PinnedNflverseResultVerifier(stats_path,expected_sha256=stats_sha256,
                                           fixture_weeks=mapping)
    observations=[]
    seen=set()
    for projection in original["projections"]:
        market=projection["market"]
        if market not in MARKETS:continue
        fixture=projection["fixture_id"]
        if fixture not in mapping:continue
        season,week=mapping[fixture]
        pid=str(projection["player_id"])
        source_row=verifier.lookup.get((season,week,pid))
        if source_row is None:continue
        column=MARKETS[market]
        if column=="passing_interceptions" and not hasattr(source_row,column):
            column="interceptions"
        if not hasattr(source_row,column):continue
        value=getattr(source_row,column)
        if value is None:continue
        try:
            actual=float(value)
        except (ValueError,TypeError):continue
        if not pd.notna(actual) or actual<0:continue
        key=(fixture,pid,market)
        if key in seen:raise ValueError("Duplicate projection observation key")
        seen.add(key)
        row={"fixture_id":fixture,"player_id":pid,"market":market,
             "actual":actual,"result_verified":True,
             "source_name":"nflverse_player_week",
             "source_record_id":f"{season}-{week}-{pid}",
             "source_sha256":stats_sha256}
        observations.append(row)
    trusted=verify_results(observations,verifier=verifier)
    scored=evaluate(original,trusted,min_sample=min_sample)
    scored.update({"stats_source_sha256":stats_sha256,
                   "schedule_source_sha256":schedule_sha256,
                   "matched_observations":len(trusted),
                   "snapshot_sha256":original["snapshot_sha256"],
                   "external_source_authenticity_certified":False,
                   "approved_wagers":0})
    return scored

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--snapshot",required=True)
    p.add_argument("--schedule",required=True)
    p.add_argument("--schedule-sha256",required=True)
    p.add_argument("--stats",required=True)
    p.add_argument("--stats-sha256",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    result=reconcile(json.loads(Path(a.snapshot).read_text()),
      schedule_path=a.schedule,schedule_sha256=a.schedule_sha256,
      stats_path=a.stats,stats_sha256=a.stats_sha256)
    target=Path(a.output);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"matched_observations":result["matched_observations"],
                      "markets":list(result["markets"]),"approved_wagers":0}))
if __name__=="__main__":main()
