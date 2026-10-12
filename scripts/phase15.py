"""Phase 15: real nflverse roster retrieval and conservative ID crosswalk.

A downloaded roster is a snapshot at fetch time, NOT a game-day active report
and never evidence about a previously captured sportsbook quote.
"""
import argparse,hashlib,json,os,shutil
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
import pandas as pd
from scripts.phase14 import identity

BASE="https://github.com/nflverse/nflverse-data/releases/download/rosters/roster_{season}.parquet"
REQUIRED={"season","team","full_name","gsis_id"}
TEAM_ALIASES={"JAC":"JAX","WSH":"WAS","OAK":"LV","SD":"LAC","STL":"LA"}
def team_code(code):
    if not isinstance(code,str):return ""
    code=code.strip().upper()
    return TEAM_ALIASES.get(code,code)
def snapshot_rows(frame,season,asof,source,sha):
    missing=REQUIRED-set(frame.columns)
    if missing:raise ValueError("Missing roster columns: "+str(sorted(missing)))
    if frame.empty:raise ValueError("Empty roster")
    if not set(pd.to_numeric(frame["season"],errors="coerce").dropna().astype(int))=={season}:
        raise ValueError("Unexpected season in roster")
    if frame["gsis_id"].notna().sum()==0:raise ValueError("No GSIS identity IDs")
    rows=[];seen=set()
    for r in frame.to_dict("records"):
        pid=r.get("gsis_id")
        name=r.get("full_name")
        team=team_code(r.get("team"))
        if pd.isna(pid) or not isinstance(name,str) or not name.strip() or not team:continue
        pid=str(pid).strip()
        if not pid or pid.lower()=="nan":continue
        key=(pid,team)
        if key in seen:continue
        seen.add(key)
        rows.append({"season":season,"team":team,"player_name":name.strip(),
                     "player_id":pid,"source":"nflverse_rosters",
                     "source_ref":source+"#sha256="+sha,
                     "as_of_utc":asof,
                     "roster_status_unverified":True,
                     "official_game_day_active_verified":False})
    if not rows:raise ValueError("No usable player identities")
    return rows
def report(rows,source,sha,asof):
    duplicates={}
    for r in rows:
        k=(r["season"],r["team"],r["player_name"].lower())
        duplicates.setdefault(k,set()).add(r["player_id"])
    return {"status":"roster_identity_snapshot_collected",
        "source":source,"source_sha256":sha,"retrieved_at_utc":asof,
        "season":rows[0]["season"],"players_with_ids":len(rows),
        "team_count":len({r["team"] for r in rows}),
        "same_name_team_conflicts":sum(len(v)>1 for v in duplicates.values()),
        "official_game_day_active_verified":False,
        "past_quotes_may_not_use_this_later_snapshot":True,
        "historical_betting_roi_verified":False}
def acquire(season,out):
    source=BASE.format(season=season)
    req=Request(source,headers={"User-Agent":"GRIDIRON-v3/1.0"})
    raw=out/("roster_"+str(season)+".parquet")
    with urlopen(req,timeout=90) as stream,raw.open("wb") as dest:
        shutil.copyfileobj(stream,dest)
    captured=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    digest=hashlib.sha256(raw.read_bytes()).hexdigest()
    roster=snapshot_rows(pd.read_parquet(raw),season,captured,source,digest)
    return roster,report(roster,source,digest,captured)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--season",type=int,default=2026)
    p.add_argument("--private-output",default="private_data/roster_2026.json")
    p.add_argument("--report-output",default="output/phase15_roster_audit.json")
    a=p.parse_args()
    if a.season<2020 or a.season>2100:p.error("Invalid season")
    private=Path(a.private_output);private.parent.mkdir(parents=True,exist_ok=True)
    roster,summary=acquire(a.season,private.parent)
    private.write_text(json.dumps(roster,indent=2));os.chmod(private,0o600)
    out=Path(a.report_output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))
if __name__=="__main__":main()
