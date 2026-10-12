"""Phase 19: matchup-specific, locked, privately encrypted GRIDIRON research ledger.

This is not a betting signal. No calibrated real-line probability or verified actives.
Public GitHub artifacts contain ONLY aggregate counts and encrypted private records.
"""
import argparse,hashlib,json,os,re
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path

import pandas as pd
from cryptography.fernet import Fernet,InvalidToken
from scripts.phase14 import identity,utc
from scripts.phase16 import team_id
from scripts.phase15 import acquire
from scripts.phase17 import fetch_history
from scripts.phase18 import (VERSION as BASE_VERSION,now,sha,jsonhash,
    fetch_schedule,forecast_prequote)
from scripts.ingest import download
from scripts.live_market import normalize
from scripts.live_odds_smoke import fetch_json,SPORT,MARKETS,DEFAULT_BOOKS

VERSION="phase19-locked-prospective-research-v1"
MARKET_NAMES=("receptions","receiving_yards")

def validate_key(value):
    if not value:raise ValueError("GRIDIRON_ARCHIVE_KEY required before any API requests")
    try:return Fernet(value.encode("ascii") if isinstance(value,str) else value)
    except (ValueError,TypeError) as exc:raise ValueError("Invalid GRIDIRON_ARCHIVE_KEY Fernet format") from None

def select_event(events,team_a,team_b,date=None,at=None):
    a,b=team_id(team_a),team_id(team_b)
    if not a or not b or a==b:raise ValueError("Two different, recognized NFL teams required")
    if date and not re.fullmatch(r"\d{4}-\d{2}-\d{2}",date):
        raise ValueError("Expected YYYY-MM-DD date")
    current=utc(at or now())
    matches=[]
    for e in events:
        home=team_id(e.get("home_team"));away=team_id(e.get("away_team"))
        try:kick=utc(e["commence_time"])
        except (KeyError,TypeError,ValueError):continue
        if {a,b}!={home,away} or kick<=current:continue
        # An optional date is matched against the UTC kickoff calendar date.
        if date and kick.date().isoformat()!=date:continue
        matches.append(e)
    if len(matches)!=1:raise ValueError("Expected one unique upcoming matchup; found "+str(len(matches)))
    return matches[0]

def freeze_before_quotes(predictions,event,metadata,archive,key,locked_at=None):
    if not predictions:raise ValueError("No forecasts to lock")
    lock_time=locked_at or now()
    if utc(lock_time)>=utc(event["commence_time"]):raise ValueError("Kickoff reached")
    if any(p["event_id"]!=event["id"] or utc(p["created_at_utc"])>utc(lock_time)
           for p in predictions):raise ValueError("Invalid prediction timestamp or event")
    content={"schema_version":1,"model_version":VERSION,
        "event_id":event["id"],
        "home_team":event["home_team"],"away_team":event["away_team"],
        "kickoff_utc":event["commence_time"],
        "locked_at_utc":lock_time,"model_metadata":metadata,
        "predictions":predictions}
    plain=json.dumps(content,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    digest=hashlib.sha256(plain).hexdigest()
    archive.mkdir(parents=True,exist_ok=True)
    path=archive/"phase19_forecasts.enc"
    path.write_bytes(key.encrypt(plain))
    os.chmod(path,0o600)
    return {"sha256":digest,"locked_at_utc":lock_time,
            "file":str(path),"count":len(predictions)}

def open_forecasts(locked,key):
    # Decrypt the actual frozen artifact rather than trusting an in-memory copy.
    path=Path(locked["file"])
    try:raw=key.decrypt(path.read_bytes())
    except InvalidToken:raise ValueError("Failed to authenticate forecast archive") from None
    if hashlib.sha256(raw).hexdigest()!=locked["sha256"]:
        raise ValueError("Forecast archive integrity mismatch")
    obj=json.loads(raw)
    if obj["locked_at_utc"]!=locked["locked_at_utc"]:
        raise ValueError("Lock timestamp mismatch")
    return obj

def reconcile(frozen,quotes,roster):
    lock=frozen["locked_at_utc"]
    forecasts={(p["event_id"],p["player_id"],p["market"]):p
               for p in frozen["predictions"]}
    status=Counter();gap=defaultdict(list);updated_gap=defaultdict(list)
    records=[];matched=set()
    for q in quotes:
        if q["event_id"]!=frozen["event_id"]:
            raise ValueError("Mismatched market event")
        if utc(q["captured_at_utc"])<=utc(lock) or utc(q["captured_at_utc"])>=utc(q["kickoff_utc"]):
            raise ValueError("Quote was not observed between forecast lock and kickoff")
        home,away=team_id(q.get("home_team")),team_id(q.get("away_team"))
        if not home or not away or home==away:
            status["unmapped_teams"]+=1;continue
        match,pid=identity({**q,"home_team":home,"away_team":away},roster)
        if match!="IDENTITY_MATCHED_NOT_ACTIVE_VERIFIED":
            status["unresolved_identity"]+=1;continue
        model=forecasts.get((q["event_id"],pid,q["market"]))
        if model is None:status["without_projection"]+=1;continue
        if utc(model["created_at_utc"])>utc(lock):
            raise ValueError("Post-lock forecast")
        difference=model["point_projection"]-float(q["line"])
        newer=utc(q["quoted_at_utc"])>utc(lock)
        status["observed_after_lock"]+=1
        if newer:status["updated_after_lock"]+=1
        else:status["existing_price_observed_after_lock"]+=1
        gap[q["market"]].append(difference)
        if newer:updated_gap[q["market"]].append(difference)
        matched.add(pid)
        records.append({**q,"player_id":pid,"locked_projection":model["point_projection"],
            "point_gap_projection_minus_line":round(difference,3),
            "price_observed_after_lock":True,"book_quote_updated_after_lock":newer,
            "model_probability":None,"expected_roi":None,
            "decision":"INSUFFICIENT_DATA","actives_verified":False})
    def metrics(values):
        return {"outcomes":len(values),"projection_above_line":sum(v>0 for v in values),
                "projection_below_line":sum(v<0 for v in values),
                "mean_absolute_gap":round(sum(abs(v) for v in values)/len(values),3) if values else None}
    report={"outcomes_total":len(quotes),"players_with_comparable_quotes":len(matched),
       "observed_after_lock":status["observed_after_lock"],
       "existing_price_observed_after_lock":status["existing_price_observed_after_lock"],
       "updated_after_lock":status["updated_after_lock"],
       "unresolved_identity":status["unresolved_identity"],
       "without_projection":status["without_projection"],
       "unmapped_teams":status["unmapped_teams"],
       "per_market":{m:{"observed_after_lock":metrics(gap[m]),
                        "updated_after_lock_only":metrics(updated_gap[m])}
                     for m in MARKET_NAMES},
       "official_bets":0,"model_probability_calibrated":False,
       "game_day_actives_verified":False,"roi_verified":False}
    return records,report

def seal_comparisons(frozen,records,report,archive,key):
    document={"schema_version":1,"frozen_forecast_sha256":
              hashlib.sha256(json.dumps(frozen,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest(),
              "ledger_created_at_utc":now(),
              "matched_quotes":records,
              "summary":report,
              "official_bets":[]}
    path=archive/"phase19_private_comparison.enc"
    path.write_bytes(key.encrypt(json.dumps(document,sort_keys=True,allow_nan=False).encode()))
    os.chmod(path,0o600)
    return path

def execute(key_text,team_a,team_b,region,date,folder):
    crypto=validate_key(key_text) # required BEFORE any paid / free API request
    events,_=fetch_json("/v4/sports/"+SPORT+"/events",{},os.getenv("ODDS_API_KEY"))
    event=select_event(events,team_a,team_b,date)
    roster,roster_audit=acquire(2026,folder)
    schedule,sch_sha=fetch_schedule(folder)
    frames=[];hashes={"roster":roster_audit["source_sha256"],"schedule":sch_sha}
    for season in range(2021,2027):
        f,meta=download(season,folder)
        frames.append(f);hashes[str(season)]=meta["sha256"]
    cutoff=now()
    predictions,model_info=forecast_prequote(roster,pd.concat(frames,ignore_index=True),
                                          schedule,event,hashes,cutoff)
    locked=freeze_before_quotes(predictions,event,model_info,folder,crypto)
    frozen=open_forecasts(locked,crypto)
    payload,quota=fetch_json("/v4/sports/"+SPORT+"/events/"+event["id"]+"/odds",
       {"regions":region,"markets":",".join(MARKETS),
        "oddsFormat":"american","bookmakers":",".join(DEFAULT_BOOKS)},
       os.getenv("ODDS_API_KEY"))
    captured=now()
    if payload.get("id")!=event["id"]:raise ValueError("Provider returned wrong event")
    quotes=normalize(payload,captured)
    rows,summary=reconcile(frozen,quotes,roster)
    seal_comparisons(frozen,rows,summary,folder,crypto)
    return {"status":"phase19_live_research_locked","version":VERSION,
        "matchup":{"team_a":team_id(team_a),"team_b":team_id(team_b),
                   "home":team_id(event["home_team"]),"away":team_id(event["away_team"]),
                   "kickoff_utc":event["commence_time"]},
        "locked_forecast_sha256":locked["sha256"],
        "locked_at_utc":locked["locked_at_utc"],"odds_captured_at_utc":captured,
        "forecast_count":len(predictions),
        "forecast_metadata":model_info,"roster_hash":roster_audit["source_sha256"],
        "data_source_hashes":hashes,"quota":quota,**summary,
        "encrypted_private_artifacts":True,"archive_retention_days":30,
        "archive_survives_runner":True,
        "independent_external_timestamp_attestation":False,
        "current_season_form_included":True,
        "opponent_scheme_and_injuries_included":False,
        "qualified_bets":0}

def decrypt_archive(path,key_text):
    key=validate_key(key_text)
    try:data=key.decrypt(Path(path).read_bytes())
    except InvalidToken:raise ValueError("Archive key invalid or encrypted file corrupted") from None
    return json.loads(data)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--live",action="store_true")
    p.add_argument("--decrypt",help="Decrypt own downloaded artifact privately; no API request")
    p.add_argument("--team-a",default="BUF")
    p.add_argument("--team-b",default="LA")
    p.add_argument("--kickoff-date",default=None,help="Optional UTC date YYYY-MM-DD")
    p.add_argument("--region",choices=("us","us2","ca"),default="us")
    p.add_argument("--summary",default="output/phase19_aggregate.json")
    p.add_argument("--decrypt-output",default=None)
    a=p.parse_args()
    key=os.environ.get("GRIDIRON_ARCHIVE_KEY")
    if a.decrypt:
        if a.live:p.error("Choose --live or --decrypt")
        doc=decrypt_archive(a.decrypt,key)
        if not a.decrypt_output:p.error("--decrypt-output required (private local file)")
        dst=Path(a.decrypt_output);dst.parent.mkdir(parents=True,exist_ok=True)
        dst.write_text(json.dumps(doc,indent=2));os.chmod(dst,0o600)
        print("Decryption successful; wrote private file.")
        return
    if not a.live:p.error("Use offline tests, or --live to opt into paid odds request")
    validate_key(key)
    if not os.getenv("ODDS_API_KEY"):p.error("ODDS_API_KEY missing")
    folder=Path("private_data");folder.mkdir(parents=True,exist_ok=True)
    results=execute(key,a.team_a,a.team_b,a.region,a.kickoff_date,folder)
    dest=Path(a.summary);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(results,indent=2))
    print(json.dumps(results,indent=2))
if __name__=="__main__":main()
