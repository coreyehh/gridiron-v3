"""GRIDIRON Phase 11: normalize authentic live NFL sportsbook quotes.

Raw odds are transient and MUST NOT be committed or uploaded as public artifacts.
No prediction or +EV claim without separate, validated pregame probabilities.
"""
import argparse
import json
import math
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from scripts.live_odds_smoke import HOST, SPORT, MARKETS, DEFAULT_BOOKS, fetch_json

SUPPORTED={"player_receptions":"receptions","player_reception_yds":"receiving_yards"}
def dt(s):
    if not s or not isinstance(s,str):
        raise ValueError("Missing timestamp")
    x=datetime.fromisoformat(s.replace("Z","+00:00"))
    if x.tzinfo is None or x.utcoffset().total_seconds()!=0:
        raise ValueError("Timestamp must be UTC")
    return x

def implied(odds):
    if isinstance(odds,bool) or not isinstance(odds,(float,int)) or not float(odds).is_integer() or abs(odds)<100:
        raise ValueError("Invalid American odds")
    return -odds/(-odds+100) if odds<0 else 100/(odds+100)

def normalize(payload, captured_at_utc):
    captured=dt(captured_at_utc)
    if not isinstance(payload,dict) or not isinstance(payload.get("bookmakers"),list):
        raise ValueError("Expected Odds API event odds object")
    event_id=payload.get("id"); kickoff=dt(payload.get("commence_time"))
    if not event_id:raise ValueError("Missing event ID")
    if captured>=kickoff:raise ValueError("Snapshot at or after kickoff")
    rows=[]
    for book in payload["bookmakers"]:
        name=book.get("key")
        if not name:continue
        for market in book.get("markets",[]):
            market_key=market.get("key")
            if market_key not in SUPPORTED:continue
            asof=dt(market.get("last_update") or book.get("last_update"))
            if asof>captured:raise ValueError("Bookmaker timestamp after capture")
            if asof>=kickoff:raise ValueError("Bookmaker quote not pregame")
            for outcome in market.get("outcomes",[]):
                side=str(outcome.get("name","")).strip().lower()
                player=outcome.get("description")
                value=outcome.get("point")
                odds=outcome.get("price")
                if side not in ("over","under") or not player or isinstance(value,bool):
                    continue
                try:
                    line=float(value)
                    if not math.isfinite(line) or line<0:continue
                    p=implied(odds)
                except (TypeError,ValueError):
                    continue
                rows.append({
                    "event_id":event_id,"home_team":payload.get("home_team"),
                    "away_team":payload.get("away_team"),
                    "kickoff_utc":payload["commence_time"],
                    "player_display_name":str(player),"player_id":None,
                    "player_id_verified":False,
                    "market":SUPPORTED[market_key],"side":side,"line":line,
                    "american_odds":int(odds),"bookmaker":name,
                    "quoted_at_utc":market.get("last_update") or book.get("last_update"),
                    "captured_at_utc":captured_at_utc,
                    "implied_probability":round(p,8),
                    "model_probability":None,"estimated_roi":None,
                    "decision":"INSUFFICIENT_DATA",
                })
    # Provider might repeat outcomes in a response: reject ambiguity.
    seen=set()
    for row in rows:
        k=(row["event_id"],row["player_display_name"],row["market"],row["side"],row["line"],row["bookmaker"])
        if k in seen:raise ValueError("Duplicate sportsbook quotation key")
        seen.add(k)
    return rows

def summarize(rows,created_at_utc):
    counts=defaultdict(int)
    books=set()
    markets=set()
    for row in rows:
        books.add(row["bookmaker"]);markets.add(row["market"])
        counts[row["bookmaker"]]+=1
    return {"status":"one_event_live_market_ingested",
            "captured_at_utc":created_at_utc,
            "quote_count":len(rows),"bookmakers":sorted(books),"markets":sorted(markets),
            "outcomes_per_book":dict(sorted(counts.items())),
            "player_identity_verified":False,
            "calibrated_probabilities_available":False,
            "bets_qualified":0,"roi_verified":False,
            "raw_quotes_published":False}

def live_check(key,region="us"):
    if not key:raise ValueError("ODDS_API_KEY missing")
    if region not in ("us","us2","ca"):raise ValueError("Unsupported region")
    events,_=fetch_json("/v4/sports/"+SPORT+"/events",{},key)
    future=sorted((e for e in events if e.get("id") and e.get("commence_time")
                   and dt(e["commence_time"])>datetime.now(timezone.utc)),
                  key=lambda e:e["commence_time"])
    if not future:
        return [],{"status":"no_upcoming_games","quote_count":0,"bets_qualified":0}
    event=future[0]
    payload,quota=fetch_json("/v4/sports/"+SPORT+"/events/"+event["id"]+"/odds",
             {"regions":region,"markets":",".join(MARKETS),
              "oddsFormat":"american","bookmakers":",".join(DEFAULT_BOOKS)},key)
    captured=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    rows=normalize(payload,captured)
    report=summarize(rows,captured)
    report["quota"]=quota
    return rows,report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",help="Offline JSON event-odds response; no API call")
    p.add_argument("--fetch",action="store_true",help="Explicitly spend API credits")
    p.add_argument("--region",choices=("us","us2","ca"),default="us")
    p.add_argument("--private-output",default="private_data/live_market.json")
    p.add_argument("--summary",default="output/live_market_summary.json")
    args=p.parse_args()
    if bool(args.input)==bool(args.fetch):
        p.error("Supply exactly one of --input or --fetch")
    if args.fetch:
        rows,report=live_check(os.getenv("ODDS_API_KEY"),args.region)
    else:
        payload=json.loads(Path(args.input).read_text())
        captured=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
        rows=normalize(payload,captured)
        report=summarize(rows,captured)
    dest=Path(args.private_output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps({"quotes":rows,"report":report},indent=2))
    os.chmod(dest,0o600)
    dest=Path(args.summary);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=="__main__":main()
