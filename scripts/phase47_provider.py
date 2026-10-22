"""Normalize saved The Odds API historical event odds. No credentials required."""
import argparse,csv,hashlib,json
from pathlib import Path
from scripts.phase47_validate_odds import validate,parse_utc
MARKETS={"player_rush_yds":"rushing_yards","player_rush_attempts":"rushing_attempts","player_receptions":"receptions","player_reception_yds":"receiving_yards","player_pass_attempts":"passing_attempts","player_pass_yds":"passing_yards"}
def normalize(payload,identities,schedules,max_age_hours=24):
    accepted,rejected=[],[]
    snapshot=payload.get("timestamp")
    event=payload.get("data") or {}
    event_id=event.get("id")
    if not snapshot or not event_id: raise ValueError("missing historical timestamp/event id")
    if event_id not in schedules: raise ValueError("unknown event id")
    schedule=schedules[event_id]
    if event.get("commence_time") and parse_utc(event["commence_time"])!=parse_utc(schedule["kickoff_utc"]): raise ValueError("kickoff mismatch")
    seen=set()
    for book in event.get("bookmakers",[]):
        for market in book.get("markets",[]):
            name=MARKETS.get(market.get("key"))
            if not name: continue
            for outcome in market.get("outcomes",[]):
                player_name=outcome.get("description")
                player_id=identities.get((event_id,player_name))
                raw=dict(event_id=event_id,player_name=player_name,player_id=player_id,season=schedule["season"],week=schedule["week"],market=name,direction=str(outcome.get("name","")).lower(),line=outcome.get("point"),american_odds=outcome.get("price"),quoted_at_utc=snapshot,kickoff_utc=schedule["kickoff_utc"],sportsbook=book.get("key"),provider="the-odds-api",source_market=market.get("key"),source_last_update=market.get("last_update") or book.get("last_update"))
                try:
                    if not player_id: raise ValueError("unresolved player identity")
                    if raw["source_last_update"] and parse_utc(raw["source_last_update"])>parse_utc(snapshot): raise ValueError("source update after snapshot")
                    record=validate(raw,max_age_hours)
                    key=(event_id,player_id,name,record["direction"],record["line"],record["american_odds"],record["sportsbook"],record["quoted_at_utc"])
                    if key not in seen: seen.add(key);accepted.append(record)
                except (ValueError,TypeError,OverflowError) as exc:
                    rejected.append({"reason":str(exc),"record":raw})
    return accepted,rejected
def run(raw_path,identity_path,schedule_path,accepted_path,rejected_path,max_age_hours=24):
    raw_bytes=Path(raw_path).read_bytes()
    payload=json.loads(raw_bytes)
    identities={}
    with Path(identity_path).open(newline="",encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key=(row["event_id"],row["player_name"])
            if key in identities and identities[key]!=row["player_id"]: raise ValueError("conflicting player identity")
            identities[key]=row["player_id"]
    schedules=json.loads(Path(schedule_path).read_text(encoding="utf-8"))
    accepted,rejected=normalize(payload,identities,schedules,max_age_hours)
    digest=hashlib.sha256(raw_bytes).hexdigest()
    for row in accepted: row["raw_sha256"]=digest
    for path in (accepted_path,rejected_path): Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(accepted_path).write_text("".join(json.dumps(r,sort_keys=True)+"\n" for r in accepted),encoding="utf-8")
    Path(rejected_path).write_text(json.dumps({"raw_sha256":digest,"rejected":rejected},indent=2)+"\n",encoding="utf-8")
    return len(accepted),len(rejected)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    for name in ("raw","identities","schedules","accepted","rejected"): p.add_argument("--"+name,required=True)
    p.add_argument("--max-age-hours",type=float,default=24)
    a=p.parse_args()
    good,bad=run(a.raw,a.identities,a.schedules,a.accepted,a.rejected,a.max_age_hours)
    print(f"accepted={good} rejected={bad}")
    if bad: raise SystemExit(1)
