"""Phase 25: price mathematics and strict real-offer eligibility checks.

OFFLINE by default. The optional live mode captures one upcoming event using
an existing Odds API secret and publishes AGGREGATE counts only, never player
quotes, lines or licensed book prices. No supported game-day official actives,
no point-in-time player calibration at real book lines: zero qualified bets.
"""
import argparse,hashlib,json,math,os
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from scripts.live_market import normalize as normalize_odds,implied,dt
from scripts.live_odds_smoke import SPORT,MARKETS,DEFAULT_BOOKS,fetch_json
from scripts.phase14 import norm
from scripts.phase16 import team_id

VERSION="phase25-market-evidence-and-price-gate-v1"
SUPPORTED={"receptions","receiving_yards"}
STALE_SECONDS=3600

def decimal_price(odds):
    implied(odds)
    return 1.+(float(odds)/100. if odds>0 else 100./abs(float(odds)))

def price_ev(win_probability,odds):
    if isinstance(win_probability,bool) or not isinstance(win_probability,(float,int)) or not math.isfinite(win_probability) or not 0<=win_probability<=1:
        raise ValueError("Verified model P(win) must be between zero and one")
    return float(win_probability)*(decimal_price(odds)-1)-(1-float(win_probability))

def joint_book_pair(over,under):
    """Equal-book, equal-event, player, market, line, consistent timestamps."""
    required=("event_id","market","player_display_name","bookmaker","kickoff_utc","quoted_at_utc","captured_at_utc")
    if any(not over.get(k) or not under.get(k) for k in required):raise ValueError("Missing pair identification")
    for k in ("event_id","market","bookmaker","kickoff_utc","player_display_name"):
        if over[k]!=under[k]:raise ValueError("Unmatched bookmaker outcome pair: "+k)
    if float(over["line"])!=float(under["line"]):raise ValueError("Different two-sided lines")
    if {over["side"],under["side"]}!={"over","under"}:raise ValueError("Expected both directions")
    if over["quoted_at_utc"]!=under["quoted_at_utc"] or over["captured_at_utc"]!=under["captured_at_utc"]:
        raise ValueError("Two-sided quotes not contemporaneous")
    quote=dt(over["quoted_at_utc"]);capture=dt(over["captured_at_utc"]);kickoff=dt(over["kickoff_utc"])
    if not quote<=capture<kickoff:raise ValueError("Not a pregame offer")
    if (capture-quote).total_seconds()>STALE_SECONDS:raise ValueError("Stale bookmaker quote")
    po=implied(over["american_odds"]);pu=implied(under["american_odds"])
    total=po+pu
    if total<.99 or total>1.40:raise ValueError("Implausible book hold or crossed quote")
    return {"hold":round(total-1,6),"over_no_vig":round(po/total,6),
            "under_no_vig":round(pu/total,6),"over_break_even":round(po,6),
            "under_break_even":round(pu,6)}

def validate_offer(outcome,seen_at):
    if outcome.get("market") not in SUPPORTED or outcome.get("side") not in ("over","under"):
        raise ValueError("Unsupported market or direction")
    if not isinstance(outcome.get("line"),(float,int)) or isinstance(outcome.get("line"),bool) or not math.isfinite(outcome["line"]) or outcome["line"]<0:
        raise ValueError("Invalid book line")
    if not outcome.get("event_id") or not outcome.get("bookmaker") or not norm(outcome.get("player_display_name")):
        raise ValueError("Missing event/book/player identity")
    cap=dt(outcome["captured_at_utc"]);source=dt(outcome["quoted_at_utc"]);kick=dt(outcome["kickoff_utc"])
    if source>cap or cap>=kick or cap>dt(seen_at):
        raise ValueError("Nonpregame/inconsistent quoted or captured timestamp")
    if (cap-source).total_seconds()>STALE_SECONDS:
        raise ValueError("Stale book line")
    implied(outcome["american_odds"])
    return True

def eligibility(outcome,projections=None,availability=None,probability=None,has_price_pair=False):
    reasons=[]
    if not outcome.get("player_id_verified"):reasons.append("player_identity_not_verified")
    if not outcome.get("projection_locked_before_quote"):reasons.append("no_locked_before_quote_projection")
    if not outcome.get("probability_line_calibrated"):reasons.append("no_real_line_probability_calibration")
    if not outcome.get("official_active_verified"):reasons.append("unverified_active")
    if not outcome.get("route_role_verified"):reasons.append("unverified_route_role")
    if not has_price_pair:reasons.append("no_same_book_two_sided_pair")
    if probability is None:reasons.append("missing_validated_win_probability")
    return {"eligible":not reasons,"reasons":reasons,"decision":"INSUFFICIENT_DATA" if reasons else "ELIGIBILITY_CHECK_PASSED"}

def analyze_quotes(quotes,captured_at_utc):
    """Public-safe aggregate; no sportsbook-player rows leak to job log or artifacts."""
    stats=Counter(); groups=defaultdict(list)
    for row in quotes:
        stats["quote_rows_seen"]+=1
        try:validate_offer(row,captured_at_utc)
        except (ValueError,TypeError,KeyError):
            stats["bad_or_stale_quotes"]+=1
            continue
        stats["valid_single_side_quotes"]+=1
        groups[(row["event_id"],row["bookmaker"],norm(row["player_display_name"]),
                row["market"],float(row["line"]))].append(row)
    for group in groups.values():
        if len(group)!=2:
            stats["unpaired_market_groups"]+=1;continue
        over=next((r for r in group if r["side"]=="over"),None)
        under=next((r for r in group if r["side"]=="under"),None)
        if over is None or under is None:
            stats["unpaired_market_groups"]+=1;continue
        try:joint_book_pair(over,under)
        except (ValueError,TypeError,KeyError):
            stats["unpaired_market_groups"]+=1;continue
        stats["valid_two_sided_pairs"]+=1
        for row in (over,under):
            gate=eligibility(row,probability=None,has_price_pair=True)
            for why in gate["reasons"]:stats["blocked_"+why]+=1
            if gate["eligible"]:stats["qualified_bets"]+=1
    return {"version":VERSION,"status":"market_integrity_audit_only",
      "counts":dict(sorted(stats.items())),
      "official_active_feed_integrated":False,
      "verified_pregame_player_roles":False,
      "frozen_real_line_calibration_integrated":False,
      "model_vs_book_qualified_edges":0,"qualified_bets":0,
      "raw_player_level_quotes_published":False,"real_bookmaker_odds_published":False}

def live_once(key,region,team_a=None,team_b=None):
    if not key:raise ValueError("Missing ODDS_API_KEY")
    if region not in ("us","us2","ca"):raise ValueError("Unsupported region")
    events,_=fetch_json("/v4/sports/"+SPORT+"/events",{},key)
    future=sorted((e for e in events if e.get("id") and e.get("commence_time")
         and dt(e["commence_time"])>datetime.now(timezone.utc)),key=lambda r:r["commence_time"])
    if team_a or team_b:
        if not team_a or not team_b or team_id(team_a)==team_id(team_b):raise ValueError("Provide two distinct valid teams")
        future=[e for e in future if {team_id(e.get("home_team")),team_id(e.get("away_team"))}==
           {team_id(team_a),team_id(team_b)}]
    if not future:
        return {"version":VERSION,"status":"no_matching_upcoming_game","counts":{},
             "qualified_bets":0,"raw_player_level_quotes_published":False,
             "sportsbook_credits_spent_on_event_quotes":False}
    game=future[0]
    payload,quota=fetch_json("/v4/sports/"+SPORT+"/events/"+game["id"]+"/odds",
      {"regions":region,"markets":",".join(MARKETS),"oddsFormat":"american",
       "bookmakers":",".join(DEFAULT_BOOKS)},key)
    captured=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    if payload.get("id")!=game["id"]:raise ValueError("Provider game mismatch")
    rows=normalize_odds(payload,captured)
    summary=analyze_quotes(rows,captured)
    summary["sportsbook_credits_spent_on_event_quotes"]=True
    summary["quota_remaining"]=quota.get("x-requests-remaining")
    summary["one_event_checked"]=True
    return summary

def markdown(result):
    counts=result.get("counts",{})
    lines=["# GRIDIRON Phase 25 — Real-book market evidence gate","",
           f"**Status:** {result['status']}","",
           "| Evidence check | Count |","|:--|--:|"]
    for key in ("quote_rows_seen","valid_single_side_quotes","valid_two_sided_pairs",
                "unpaired_market_groups","bad_or_stale_quotes"):
        lines.append(f"| {key.replace('_',' ')} | {counts.get(key,0)} |")
    lines+=["","**Official bets cleared: 0.** No independently verified game-day active status, target-route participation, and calibrated prequote probabilities for actual sportsbook lines have been integrated.",
       "Both sides require the SAME bookmaker, player, game, threshold and capture window for no-vig comparison. Unlike point-to-line gaps, price math alone cannot certify a bet.",
       "**No licensed player/book odds were printed, saved, committed or uploaded.**",
       ""]
    return "\n".join(lines)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--live",action="store_true",help="Explicit paid one-event odds request")
    p.add_argument("--region",choices=("us","us2","ca"),default="us")
    p.add_argument("--team-a",default=None)
    p.add_argument("--team-b",default=None)
    p.add_argument("--output",default="output/phase25_aggregate.json")
    args=p.parse_args()
    if args.live:
        result=live_once(os.getenv("ODDS_API_KEY"),args.region,args.team_a,args.team_b)
    else:
        result={"version":VERSION,"status":"offline_price_math_and_gate_tests_only",
          "counts":{},"qualified_bets":0,"raw_player_level_quotes_published":False,
          "sportsbook_credits_spent_on_event_quotes":False}
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2))
    msg=markdown(result);print(msg)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as summary:summary.write(msg)
if __name__=="__main__":main()
