"""Phase 32: locked 2026 forecasts vs authentic pregame sportsbook offers.

Default offline: no network and no API credits. One live event ONLY with explicit
opt-in. Real bookmaker player lines and prices stay ephemeral in memory; public
output contains aggregate diagnostics, NEVER player/book/line combinations.
Comparing point projections with a line is NOT a calibrated +EV probability.
"""
import argparse,json,os
from collections import Counter,defaultdict
from datetime import datetime,timezone,timedelta
from pathlib import Path
from scripts.phase31_accountability import verify_snapshot
from scripts.phase28_snap_participation import name_key
from scripts.phase16 import team_id
from scripts.phase25_market_gate import validate_offer,joint_book_pair
from scripts.live_market import normalize as normalize_odds,dt
from scripts.live_odds_smoke import SPORT,MARKETS,DEFAULT_BOOKS,fetch_json

VERSION="phase32-frozen-forecast-vs-live-market-audit-v1"
MARKET_FIELD={"receptions":"receptions","receiving_yards":"receiving_yards"}

def selected_fixture(snapshot,event):
    """Require exact opponents and kickoff calendar compatibility.

    Kickoff is UTC, NFL fixture gameday is local calendar date; UTC can be
    the next day. Do not accept unrelated games with the same teams.
    """
    verify_snapshot(snapshot)
    a,b=team_id(event.get("home_team")),team_id(event.get("away_team"))
    if not a or not b or a==b:raise ValueError("Unrecognized event clubs")
    kickoff=dt(event.get("commence_time"))
    if kickoff.year!=snapshot["season"]:raise ValueError("Event not in snapshot season")
    matches=[]
    for f in snapshot["fixtures"]:
        if (f["home"],f["away"])!=(a,b):continue
        gameday=datetime.fromisoformat(f["gameday"]).date()
        if kickoff.date() not in (gameday,gameday+timedelta(days=1)):continue
        matches.append(f)
    if len(matches)!=1:raise ValueError("No unique frozen fixture for sportsbook event")
    lock=dt(snapshot["created_at_utc"].replace("+00:00","Z"))
    if lock>=kickoff:raise ValueError("Snapshot locked after kickoff")
    return matches[0]

def matched_forecasts(snapshot,fixture):
    """Only unique historical player names on *the frozen fixture* may match.

    A sportsbook row doesn't supply a validated GSIS player ID. Exact matching
    remains a roster-name proxy and must not be marked identity_verified.
    """
    byname=defaultdict(list)
    for r in snapshot["forecasts"]:
        if r["fixture_id"]==fixture["id"]:
            byname[name_key(r["player_name"])].append(r)
    return {name:rs[0] for name,rs in byname.items() if name and len(rs)==1},{
        "ambiguous_snapshot_names":sum(len(rs)>1 for rs in byname.values()),
        "frozen_fixture_forecasts":sum(len(rs) for rs in byname.values())}

def compare(snapshot,event,rows,captured_at):
    fixture=selected_fixture(snapshot,event)
    frozen,meta=matched_forecasts(snapshot,fixture)
    cap=dt(captured_at)
    lock=dt(snapshot["created_at_utc"].replace("+00:00","Z"))
    kickoff=dt(event["commence_time"])
    if not lock<cap<kickoff:raise ValueError("Must capture after frozen lock and before kickoff")
    counts=Counter();groups=defaultdict(list);matched_names=set()
    for row in rows:
        counts["quote_rows_seen"]+=1
        if row.get("event_id")!=event.get("id"):
            counts["wrong_event"]+=1;continue
        try:validate_offer(row,captured_at)
        except (ValueError,KeyError,TypeError):
            counts["stale_or_invalid_quotes"]+=1;continue
        counts["valid_quote_rows"]+=1
        key=name_key(row["player_display_name"])
        pred=frozen.get(key)
        if pred is None:
            counts["unmatched_or_ambiguous_player_rows"]+=1;continue
        if row["market"] not in MARKET_FIELD:
            counts["unsupported_market"]+=1;continue
        counts["matched_player_market_sides"]+=1
        matched_names.add(key)
        if dt(row["quoted_at_utc"])<lock:
            counts["quote_source_predates_frozen_lock"]+=1
        groups[(row["event_id"],row["bookmaker"],key,row["market"],row["line"])].append((row,pred))
    for pair in groups.values():
        if len(pair)!=2:
            counts["unpaired_matched_market_groups"]+=1;continue
        upper=next((r for r,p in pair if r["side"]=="over"),None)
        lower=next((r for r,p in pair if r["side"]=="under"),None)
        if upper is None or lower is None:
            counts["unpaired_matched_market_groups"]+=1;continue
        try:market=joint_book_pair(upper,lower)
        except (ValueError,KeyError,TypeError):
            counts["unpaired_matched_market_groups"]+=1;continue
        pred=pair[0][1]
        projected=float(pred[MARKET_FIELD[upper["market"]]])
        gap=projected-float(upper["line"])
        counts["matched_valid_two_sided_pairs"]+=1
        counts["projection_above_line" if gap>0 else "projection_below_line" if gap<0 else "projection_equal_to_line"]+=1
        if abs(gap)>=5 and upper["market"]=="receiving_yards":
            counts["receiving_yards_absolute_gap_5_or_more"]+=1
        if abs(gap)>=1 and upper["market"]=="receptions":
            counts["receptions_absolute_gap_1_or_more"]+=1
        if dt(upper["quoted_at_utc"])>=lock:
            counts["book_source_timestamp_after_lock"]+=1
        counts["matched_receptions_pairs" if upper["market"]=="receptions" else "matched_receiving_yards_pairs"]+=1
    counts["unique_player_names_matched"] = len(matched_names)
    # No per-player prices, lines, bookmaker names, quoted timestamps or gaps.
    return {"version":VERSION,"status":"price_discovery_comparison_only",
        "matched_fixture":fixture["id"],
        "frozen_snapshot_sha256":snapshot["payload_sha256"],
        "snapshot_locked_at_utc":snapshot["created_at_utc"],
        "counts":dict(sorted(counts.items())),**meta,
        "market_rows_published":False,"licensed_book_prices_published":False,
        "player_specific_edges_published":False,
        "identity_verified_by_provider_id":False,
        "game_day_active_status_verified":False,
        "matched_real_line_probabilities_calibrated":False,
        "projected_gap_is_not_expected_value":True,
        "qualified_bets":0}

def discover(key,snapshot,selected_id=""):
    if not key:raise ValueError("Missing ODDS_API_KEY")
    if selected_id and (not selected_id.isalnum() or len(selected_id)>128):
        raise ValueError("Invalid event ID")
    events,_=fetch_json("/v4/sports/"+SPORT+"/events",{},key)
    if not isinstance(events,list):raise ValueError("Bad event discovery response")
    now=datetime.now(timezone.utc)
    eligible=[]
    for e in events:
        if not e.get("id") or not e.get("commence_time"):continue
        try:
            if dt(e["commence_time"])<=now:continue
            selected_fixture(snapshot,e)
        except ValueError:continue
        if selected_id and e["id"]!=selected_id:continue
        eligible.append(e)
    return sorted(eligible,key=lambda e:e["commence_time"])

def run(snapshot,request_live=False,key=None,region="us",event_id=""):
    verify_snapshot(snapshot)
    if not request_live:
        return {"version":VERSION,"status":"offline_no_credits",
          "snapshot_forecasts":len(snapshot["forecasts"]),
          "snapshot_fixtures":len(snapshot["fixtures"]),
          "forecast_lock_verified":True,
          "live_event_quote_request_made":False,
          "qualified_bets":0}
    if region not in ("us","us2","ca"):raise ValueError("Unknown region")
    if not key:raise ValueError("Missing ODDS_API_KEY")
    events=discover(key,snapshot,event_id)
    if not events:
        return {"version":VERSION,"status":"no_matching_future_frozen_event",
           "live_event_quote_request_made":False,
           "qualified_bets":0}
    event=events[0]
    # Discovery and the fixture validation happen BEFORE spending on a player market.
    selected_fixture(snapshot,event)
    payload,quota=fetch_json("/v4/sports/"+SPORT+"/events/"+event["id"]+"/odds",{
       "regions":region,"markets":",".join(MARKETS),"oddsFormat":"american",
       "bookmakers":",".join(DEFAULT_BOOKS)},key)
    if payload.get("id")!=event["id"] or payload.get("commence_time")!=event["commence_time"]:
        raise ValueError("Odds payload event/kickoff changed")
    if {team_id(payload.get("home_team")),team_id(payload.get("away_team"))}!={
        team_id(event.get("home_team")),team_id(event.get("away_team"))}:
        raise ValueError("Odds payload home/away mismatch")
    stamp=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    quotes=normalize_odds(payload,stamp)
    result=compare(snapshot,event,quotes,stamp)
    result["live_event_quote_request_made"]=True
    result["quota_remaining"]=quota.get("x-requests-remaining")
    result["region"]=region
    return result

def markdown(result):
    counts=result.get("counts",{})
    lines=["# GRIDIRON Phase 32 — Locked forecasts versus real offered props","",
      f"**Status:** {result['status']}","",
      f"**Frozen forecast lock validated:** {result.get('forecast_lock_verified',bool(result.get('frozen_snapshot_sha256')))}",
      f"**Live paid event odds call made:** {result.get('live_event_quote_request_made',False)}","",
      "## Source and matching audit","",
      "| Check | Count |","|:--|--:|"]
    for k in ("quote_rows_seen","valid_quote_rows","stale_or_invalid_quotes",
       "matched_player_market_sides","unique_player_names_matched",
       "matched_valid_two_sided_pairs","matched_receptions_pairs",
       "matched_receiving_yards_pairs","unmatched_or_ambiguous_player_rows",
       "quote_source_predates_frozen_lock","projection_above_line",
       "projection_below_line","receiving_yards_absolute_gap_5_or_more",
       "receptions_absolute_gap_1_or_more"):
        lines.append(f"| {k.replace('_',' ')} | {counts.get(k,0)} |")
    lines+=["","**Zero qualified bets.** Projection-minus-book line gaps are not model probabilities, evidence of +EV, or a recommendation.",
      "**No individual sportsbook names, player odds, thresholds, matched player lines or quoted market records are exported.**",
      "Identity is a unique exact normalized player-name match within the frozen game; sportsbook GSIS IDs, game-day actives, real-line probability calibration and EV remain unverified.",""]
    return "\n".join(lines)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--snapshot",default="snapshots/phase31/2026-week-06.json")
    p.add_argument("--live",action="store_true",help="Explicitly opt into one paid NFL event odds request")
    p.add_argument("--region",choices=("us","us2","ca"),default="us")
    p.add_argument("--event-id",default="",help="Optional provider event ID; blank picks first eligible frozen event")
    p.add_argument("--output",default="output/phase32_market_match_aggregate.json")
    a=p.parse_args()
    snapshot=json.loads(Path(a.snapshot).read_text())
    result=run(snapshot,a.live,os.getenv("ODDS_API_KEY"),a.region,a.event_id)
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2))
    page=markdown(result);print(page)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write(page)
if __name__=="__main__":main()
