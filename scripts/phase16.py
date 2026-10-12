"""Phase 16: real-time roster-first NFL player prop matching audit.

Only explicit manual --live makes an Odds API request. Results are aggregate-only;
player names, individual lines, and credentials never enter logs or public artifacts.
"""
import argparse,json,os
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path

from scripts.phase14 import norm,utc,identity
from scripts.phase15 import acquire
from scripts.live_market import live_check

TEAMS={
"Arizona Cardinals":"ARI","Atlanta Falcons":"ATL","Baltimore Ravens":"BAL",
"Buffalo Bills":"BUF","Carolina Panthers":"CAR","Chicago Bears":"CHI",
"Cincinnati Bengals":"CIN","Cleveland Browns":"CLE","Dallas Cowboys":"DAL",
"Denver Broncos":"DEN","Detroit Lions":"DET","Green Bay Packers":"GB",
"Houston Texans":"HOU","Indianapolis Colts":"IND","Jacksonville Jaguars":"JAX",
"Kansas City Chiefs":"KC","Las Vegas Raiders":"LV","Los Angeles Chargers":"LAC",
"Los Angeles Rams":"LA","Miami Dolphins":"MIA","Minnesota Vikings":"MIN",
"New England Patriots":"NE","New Orleans Saints":"NO","New York Giants":"NYG",
"New York Jets":"NYJ","Philadelphia Eagles":"PHI","Pittsburgh Steelers":"PIT",
"San Francisco 49ers":"SF","Seattle Seahawks":"SEA","Tampa Bay Buccaneers":"TB",
"Tennessee Titans":"TEN","Washington Commanders":"WAS"}
TEAM_ABBRS=set(TEAMS.values())
ALIASES={"JAC":"JAX","WSH":"WAS","LAR":"LA","GNB":"GB","KAN":"KC",
         "NWE":"NE","NOR":"NO","SFO":"SF","TAM":"TB"}
def team_id(raw):
    if not isinstance(raw,str):return None
    raw=raw.strip()
    if raw in TEAMS:return TEAMS[raw]
    code=raw.upper()
    if code in TEAM_ABBRS:return code
    code=ALIASES.get(code)
    return code if code in TEAM_ABBRS else None

def players(rows,roster):
    if not isinstance(rows,list) or not isinstance(roster,list):raise ValueError("Invalid input lists")
    groups=defaultdict(list)
    for q in rows:
        key=(q.get("event_id"),q.get("season"),norm(q.get("player_display_name")))
        groups[key].append(q)
    statuses=Counter();market_counts=Counter();examples=[];evaluated=0
    for group in groups.values():
        q=group[0]
        home=team_id(q.get("home_team"));away=team_id(q.get("away_team"))
        if not home or not away or home==away:
            status="UNMAPPED_EVENT_TEAM"
        elif any(team_id(r.get("home_team"))!=home or
                 team_id(r.get("away_team"))!=away or
                 r.get("season")!=q.get("season") for r in group):
            status="INCONSISTENT_EVENT"
        else:
            checked={**q,"home_team":home,"away_team":away}
            try:
                status,_=identity(checked,roster)
            except (ValueError,KeyError,TypeError):
                status="INVALID_QUOTE_TIMESTAMPS"
        statuses[status]+=1; evaluated+=1
        for r in group:market_counts[r.get("market")]+=1
    matched=statuses["IDENTITY_MATCHED_NOT_ACTIVE_VERIFIED"]
    total=len(groups)
    return {"unique_event_players":total,
        "identity_matched":matched,
        "unresolved":statuses["UNRESOLVED"],
        "ambiguous":statuses["AMBIGUOUS"],
        "unmapped_event_teams":statuses["UNMAPPED_EVENT_TEAM"],
        "inconsistent_events":statuses["INCONSISTENT_EVENT"],
        "invalid_quote_timestamps":statuses["INVALID_QUOTE_TIMESTAMPS"],
        "identity_match_rate_pct":round(100*matched/total,2) if total else None,
        "quote_outcome_count":len(rows),
        "market_outcome_counts":dict(sorted(market_counts.items())),
        "decision":"INSUFFICIENT_DATA",
        "verified_game_day_active":False,"bets_qualified":0}

def audit(roster,roster_audit,quotes,odds_audit):
    if not roster_audit.get("retrieved_at_utc"):raise ValueError("Roster retrieval time missing")
    if quotes:
        for q in quotes:
            # Critical chronological constraint: no retroactive roster lookups.
            if utc(roster_audit["retrieved_at_utc"])>utc(q["captured_at_utc"]):
                raise ValueError("Quote snapshot predates roster snapshot")
            if utc(q["captured_at_utc"])>=utc(q["kickoff_utc"]):
                raise ValueError("Snapshot is postkickoff")
            if q.get("season")!=roster_audit["season"]:
                raise ValueError("Roster season does not match quote")
    metrics=players(quotes,roster)
    return {"status":"phase16_prospective_identity_audit",
       "created_at_utc":datetime.now(timezone.utc).isoformat(),
       "roster_source_sha256":roster_audit.get("source_sha256"),
       "roster_retrieved_at_utc":roster_audit["retrieved_at_utc"],
       "roster_identity_records":len(roster),
       "roster_season":roster_audit["season"],
       "odds_snapshot_captured_at_utc":odds_audit.get("captured_at_utc"),
       "books":odds_audit.get("bookmakers",[]),
       "quota":odds_audit.get("quota",{}),
       **metrics,"raw_quotes_published":False,
       "historical_bet_roi_verified":False}

def live(key,region):
    # Roster fetched first in this SAME run; quote timestamp must be later.
    folder=Path("private_data");folder.mkdir(parents=True,exist_ok=True)
    roster,roster_audit=acquire(2026,folder)
    quotes,odds_audit=live_check(key,region)
    return audit(roster,roster_audit,quotes,odds_audit)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--live",action="store_true",help="Explicitly use API credits for one game")
    p.add_argument("--region",choices=("us","us2","ca"),default="us")
    p.add_argument("--roster",help="Offline roster JSON")
    p.add_argument("--roster-audit",help="Offline roster audit JSON")
    p.add_argument("--market",help="Offline Phase11 private quotes JSON")
    p.add_argument("--output",default="output/phase16_identity_audit.json")
    a=p.parse_args()
    if a.live:
        if a.roster or a.market or a.roster_audit:p.error("No offline files allowed with --live")
        result=live(os.environ.get("ODDS_API_KEY"),a.region)
    else:
        if not all((a.roster,a.roster_audit,a.market)):
            p.error("Offline mode requires --roster --roster-audit and --market")
        roster=json.loads(Path(a.roster).read_text())
        roster_audit=json.loads(Path(a.roster_audit).read_text())
        market=json.loads(Path(a.market).read_text())
        result=audit(roster,roster_audit,market["quotes"],market.get("report",{}))
    dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=="__main__":main()
