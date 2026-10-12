"""Quota-safe LIVE NFL prop API smoke test. No historical odds / EV claims.

Set ODDS_API_KEY as GitHub Actions secret. Run manually; no scheduled paid calls.
Default: discover events only (zero credits); optionally query ONE game's RB
reception and receiving-yard props (at most two market-regions).
Never print keys, full URLs with credentials, or individual licensed odds rows.
"""
import argparse, json, os, sys
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

HOST="https://api.the-odds-api.com"
SPORT="americanfootball_nfl"
MARKETS=("player_receptions","player_reception_yds")
DEFAULT_BOOKS=("draftkings","fanduel","betmgm","betrivers")
def now(): return datetime.now(timezone.utc).isoformat()
def fetch_json(path,params,key):
    params=dict(params)
    params["apiKey"]=key
    req=Request(HOST+path+"?"+urlencode(params),headers={"User-Agent":"GRIDIRON-v3-coverage-check/1.0"})
    try:
        with urlopen(req,timeout=30) as response:
            data=json.loads(response.read().decode("utf-8"))
            headers={k:response.headers.get(k) for k in
                     ("x-requests-remaining","x-requests-used","x-requests-last")}
        return data,headers
    except HTTPError as e:
        # API might include credentials in request URL; never expose exception repr or raw body.
        raise RuntimeError("API returned HTTP "+str(e.code)) from None
    except URLError:
        raise RuntimeError("API network request failed") from None

def summarize(response,expected_markets):
    if not isinstance(response,dict) or not isinstance(response.get("bookmakers"),list):
        raise ValueError("Unexpected bookmaker odds response")
    providers={}
    count=0
    for b in response["bookmakers"]:
        provider=b.get("key")
        if not isinstance(provider,str):continue
        summary={"markets":[],"outcomes":0}
        for m in b.get("markets",[]):
            if m.get("key") not in expected_markets:continue
            outcomes=m.get("outcomes",[])
            # Keep only market names/counts; never publish player names or lines.
            summary["markets"].append(m["key"])
            summary["outcomes"]+=len(outcomes)
            count+=len(outcomes)
        if summary["markets"]:providers[provider]=summary
    return providers,count

def check(key,enable_odds=False,region="us",bookmakers=DEFAULT_BOOKS):
    if not key:raise ValueError("ODDS_API_KEY secret missing")
    if region not in ("us","us2","ca"):raise ValueError("Unsupported region")
    result={"created_at_utc":now(),"status":"events_discovery_only",
            "sport":SPORT,"region":region,
            "events_discovered":0,"odds_request_made":False,
            "historical_data_available":False,"roi_verified":False,
            "max_requested_markets_per_event":2,
            "quota":{},"provider_coverage":{}}
    events,quota=fetch_json("/v4/sports/"+SPORT+"/events",{},key)
    if not isinstance(events,list):raise ValueError("Unexpected events response")
    result["events_discovered"]=len(events)
    result["quota"]=quota
    if not enable_odds or not events:
        result["status"]="events_found" if events else "no_upcoming_events"
        return result
    future=sorted([e for e in events if e.get("id") and e.get("commence_time")],key=lambda e:e["commence_time"])
    if not future:
        result["status"]="no_upcoming_events"
        return result
    e=future[0]
    odds,quota=fetch_json("/v4/sports/"+SPORT+"/events/"+e["id"]+"/odds",
        {"regions":region,"markets":",".join(MARKETS),"oddsFormat":"american",
         "bookmakers":",".join(bookmakers)},key)
    providers,count=summarize(odds,set(MARKETS))
    result.update(status="prop_quote_coverage_checked",odds_request_made=True,
        market_keys_requested=list(MARKETS),provider_coverage=providers,
        outcome_count=count,quota=quota)
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",default="output/live_odds_check.json")
    p.add_argument("--enable-odds",action="store_true",
                   help="SPENDS API credits: one event, up to two player-prop markets")
    p.add_argument("--region",choices=["us","us2","ca"],default="us")
    args=p.parse_args()
    try:
        result=check(os.getenv("ODDS_API_KEY"),args.enable_odds,args.region)
    except (ValueError,RuntimeError) as exc:
        result={"created_at_utc":now(),"status":"check_failed","reason":str(exc),
                "odds_request_made":False,"roi_verified":False}
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    if result["status"]=="check_failed":sys.exit(1)

if __name__=="__main__":main()
