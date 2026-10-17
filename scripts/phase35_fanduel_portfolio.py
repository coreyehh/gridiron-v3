"""Phase 35 — FanDuel-only singles, correlation-aware portfolio and units.

Public mode ALWAYS fail-closed: no official actives feed and no prospectively
validated real-line probabilities. No actual wagers can be qualified yet.
Optional authenticated FanDuel one-event live audit is AGGREGATE-ONLY.
"""
import argparse,hashlib,json,math,os
from collections import Counter,defaultdict
from datetime import datetime,timezone
from itertools import combinations
from pathlib import Path
from scripts.phase31_accountability import verify_snapshot,canonical
from scripts.phase34_decision_dashboard import build as research_dashboard
from scripts.phase25_market_gate import joint_book_pair,validate_offer,decimal_price,price_ev
from scripts.phase32_market_matching import selected_fixture,matched_forecasts,discover
from scripts.phase28_snap_participation import name_key
from scripts.live_odds_smoke import SPORT,MARKETS,fetch_json
from scripts.live_market import normalize as normalize_odds,dt

VERSION="phase35-fanduel-price-portfolio-gate-v1"
BOOK="fanduel"
MAX_PARLAY_LEGS=5
DEFAULT_BANKROLL=1000.0
DEFAULT_UNIT_PERCENT=1.0
# Caps, not promises to wager. Applies only to independently approved picks.
MAX_SINGLE_UNITS=1.0
MAX_PARLAY_UNITS={2:0.5,3:0.4,4:0.25,5:0.1}
MAX_TOTAL_UNITS=3.0
MIN_EV=0.03

def finite_amount(value,name,positive=False):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError(name+" must be a finite number")
    if (value<=0 if positive else value<0):raise ValueError(name+" outside allowed range")
    return float(value)

def bankroll_config(bankroll=DEFAULT_BANKROLL,unit_pct=DEFAULT_UNIT_PERCENT):
    b=finite_amount(bankroll,"bankroll",True)
    u=finite_amount(unit_pct,"unit_percent",True)
    if u>2:raise ValueError("Unit percentage over 2% maximum")
    return {"bankroll":round(b,2),"unit_percent":u,
       "unit_value":round(b*u/100,2),
       "total_stake_cap":round(b*u/100*MAX_TOTAL_UNITS,2),
       "max_single_units":MAX_SINGLE_UNITS,
       "max_total_units":MAX_TOTAL_UNITS,
       "parlay_unit_caps":{str(n):v for n,v in MAX_PARLAY_UNITS.items()}}

def validate_candidate(candidate):
    """Only independently verified *real* pregame inputs may enter sizing."""
    reasons=[]
    if candidate.get("bookmaker")!=BOOK:reasons.append("not_fanduel")
    if not candidate.get("same_book_two_sided_pair_validated"):reasons.append("missing_same_book_market_pair")
    if not candidate.get("snapshot_locked_before_offer"):reasons.append("missing_frozen_forecast")
    if not candidate.get("player_identity_verified"):reasons.append("unverified_player_identity")
    if not candidate.get("official_game_day_active_verified"):reasons.append("unverified_game_day_actives")
    if not candidate.get("role_and_route_verified"):reasons.append("unverified_route_role")
    if not candidate.get("real_line_probability_independently_validated"):reasons.append("unvalidated_real_line_probability")
    if not candidate.get("pregame_quote_fresh"):reasons.append("quote_stale_or_not_pregame")
    if not candidate.get("football_context_verified"):reasons.append("football_context_unverified")
    probability=candidate.get("p_win")
    odds=candidate.get("american_odds")
    try:
        if probability is None:raise ValueError("Missing probability")
        if isinstance(probability,bool):raise ValueError("Boolean probability")
        probability=finite_amount(probability,"probability")
        if probability>1:raise ValueError("Probability over 1")
        ev=price_ev(probability,odds)
    except (ValueError,TypeError,ZeroDivisionError):
        reasons.append("missing_or_invalid_price_probability")
        ev=None
    if ev is not None and ev<MIN_EV:reasons.append("insufficient_price_edge")
    return {"qualified":not reasons,"reasons":reasons,
       "estimated_roi":round(ev,5) if ev is not None and not reasons else None,
       "break_even_probability":round(1/decimal_price(odds),6) if not reasons else None}

def single_stake(candidate,config):
    verdict=validate_candidate(candidate)
    if not verdict["qualified"]:
        return {"decision":"PASS","units":0.,"stake":0.,"reasons":verdict["reasons"]}
    # Fractional Kelly capped to prevent an underpowered probability estimate
    # from generating unlimited stakes; still requires independently qualified p.
    p=float(candidate["p_win"]);d=decimal_price(candidate["american_odds"])
    fraction=max(0.,(p*d-1)/(d-1))*.25
    unit_pct=config["unit_percent"]/100
    units=min(MAX_SINGLE_UNITS,fraction/unit_pct)
    return {"decision":"QUALIFIED_RESEARCH_PROPOSAL","units":round(units,3),
       "stake":round(units*config["unit_value"],2),
       "reasons":[],"estimated_roi":verdict["estimated_roi"]}

def validate_parlay(legs,combined_american_odds=None,joint_probability=None,
                    payout_source_verified=False,joint_model_validated=False,
                    fanduel_acceptance_verified=False):
    if not 2<=len(legs)<=MAX_PARLAY_LEGS:raise ValueError("Parlays require 2-5 legs")
    reasons=[]
    if any(not validate_candidate(x)["qualified"] for x in legs):
        reasons.append("one_or_more_legs_unqualified")
    ids=[(x.get("event_id"),x.get("player_id"),x.get("market")) for x in legs]
    if len(set(ids))!=len(ids):reasons.append("duplicate_or_opposing_player_market")
    if any(x.get("bookmaker")!=BOOK for x in legs):reasons.append("not_all_fanduel")
    if not joint_model_validated:reasons.append("no_validated_joint_distribution")
    if not payout_source_verified or not fanduel_acceptance_verified:
        reasons.append("no_verified_fanduel_combined_quote_or_acceptance")
    ev=None
    try:
        if joint_probability is None or isinstance(joint_probability,bool):
            raise ValueError("Missing joint probability")
        joint_probability=finite_amount(joint_probability,"joint_probability")
        if joint_probability>1:raise ValueError("Probability too large")
        ev=price_ev(joint_probability,combined_american_odds)
    except (ValueError,TypeError,ZeroDivisionError):
        reasons.append("no_valid_joint_probability_and_parlay_price")
    if ev is not None and ev<MIN_EV:reasons.append("insufficient_joint_price_edge")
    return {"eligible":not reasons,"reasons":reasons,
       "joint_estimated_roi":round(ev,5) if ev is not None and not reasons else None,
       "units":0. if reasons else None}

def portfolio(candidates,bankroll=DEFAULT_BANKROLL,unit_pct=DEFAULT_UNIT_PERCENT):
    cfg=bankroll_config(bankroll,unit_pct)
    singles=[]
    remaining=cfg["max_total_units"]
    # Sort only qualified singles; an unqualified high nominal EV NEVER ranks up.
    qualified=[]
    rejected=Counter()
    for c in candidates:
        gate=validate_candidate(c)
        if not gate["qualified"]:
            rejected.update(gate["reasons"]);continue
        qualified.append((gate["estimated_roi"],c))
    for _ev,c in sorted(qualified,key=lambda pair:-pair[0]):
        stake=single_stake(c,cfg)
        units=min(stake["units"],remaining)
        if units<=0:continue
        remaining-=units
        singles.append({"selection_id":c.get("selection_id"),
          "units":round(units,3),"stake":round(units*cfg["unit_value"],2),
          "price_ev":_ev,"decision":"QUALIFIED_RESEARCH_PROPOSAL"})
    # No parlays without a separately verified accepted FanDuel combined price
    # AND a real joint distribution; never multiply individual book odds.
    return {"bankroll":cfg,"qualified_singles":singles,
        "qualified_parlays":{str(n):[] for n in range(2,6)},
        "parlay_slots":[{"legs":n,"cap_units":MAX_PARLAY_UNITS[n],
           "decision":"PASS_UNTIL_JOINT_PRICE_AND_PROBABILITY_VERIFIED"}
             for n in range(2,6)],
        "rejected_reasons":dict(sorted(rejected.items())),
        "total_units":round(cfg["max_total_units"]-remaining,3),
        "total_stake":round((cfg["max_total_units"]-remaining)*cfg["unit_value"],2)}

def review_fanduel(snapshot,payload,captured_at):
    """Check actual FanDuel matching in memory; publish no licensed quote rows."""
    if not isinstance(payload,dict):raise ValueError("Bad event payload")
    event={"id":payload.get("id"),"commence_time":payload.get("commence_time"),
      "home_team":payload.get("home_team"),"away_team":payload.get("away_team")}
    fixture=selected_fixture(snapshot,event)
    lock=dt(snapshot["created_at_utc"].replace("+00:00","Z"))
    if not lock<dt(captured_at)<dt(event["commence_time"]):
        raise ValueError("Quote capture outside pregame snapshot window")
    bookmakers=payload.get("bookmakers",[])
    if any(b.get("key")!=BOOK for b in bookmakers):
        raise ValueError("Non-FanDuel bookmaker in FanDuel-only response")
    rows=normalize_odds(payload,captured_at)
    known,_=matched_forecasts(snapshot,fixture)
    stats=Counter();groups=defaultdict(list)
    for r in rows:
        stats["quote_sides"]+=1
        if r["bookmaker"]!=BOOK:raise ValueError("Non-FanDuel quote")
        try:validate_offer(r,captured_at)
        except (ValueError,KeyError,TypeError):
            stats["invalid_quote_sides"]+=1;continue
        player=known.get(name_key(r["player_display_name"]))
        if player is None:
            stats["unmatched_player_sides"]+=1;continue
        stats["name_matched_quote_sides"]+=1
        groups[(r["event_id"],name_key(r["player_display_name"]),r["market"],
                r["line"])].append(r)
    for group in groups.values():
        if len(group)!=2:
            stats["unpaired_groups"]+=1;continue
        over=next((r for r in group if r["side"]=="over"),None)
        under=next((r for r in group if r["side"]=="under"),None)
        if over is None or under is None:
            stats["unpaired_groups"]+=1;continue
        try:joint_book_pair(over,under)
        except (ValueError,KeyError,TypeError):
            stats["unpaired_groups"]+=1;continue
        stats["valid_fanduel_pairs"]+=1
    return {"status":"fanduel_single_event_private_quote_evidence_audit",
       "matched_fixture":fixture["id"],"counts":dict(sorted(stats.items())),
       "player_id_provider_verified":False,
       "official_game_day_actives_verified":False,
       "real_offer_calibrated_probabilities_verified":False,
       "fanduel_sgp_joint_prices_available":False,
       "qualified_singles":0,"qualified_parlays":0,
       "individual_book_quotes_published":False}

def live_fanduel_once(snapshot,key,region="us",event_id=""):
    if not key:raise ValueError("ODDS_API_KEY missing")
    if region not in ("us","us2","ca"):raise ValueError("Invalid region")
    selected=discover(key,snapshot,event_id)
    if not selected:
        return {"status":"no_future_frozen_event","paid_event_odds_request_made":False,
           "qualified_singles":0,"qualified_parlays":0}
    event=selected[0]
    payload,quota=fetch_json("/v4/sports/"+SPORT+"/events/"+event["id"]+"/odds",{
       "regions":region,"markets":",".join(MARKETS),"oddsFormat":"american",
       "bookmakers":BOOK},key)
    if payload.get("id")!=event["id"] or payload.get("commence_time")!=event["commence_time"]:
        raise ValueError("Provider switched event/kickoff")
    audit=review_fanduel(snapshot,payload,
           datetime.now(timezone.utc).isoformat().replace("+00:00","Z"))
    audit["paid_event_odds_request_made"]=True
    audit["quota_remaining"]=quota.get("x-requests-remaining")
    return audit

def create_ledger(board,port,market_audit=None):
    """Immutable audit intent; no picks fabricated and no private book quotes."""
    data={"version":VERSION,"season":board["season"],"week":board["week"],
      "frozen_forecast_sha256":board["forecast_lock_sha256"],
      "captured_at_utc":datetime.now(timezone.utc).isoformat(),
      "bookmaker":"fanduel","research_player_rows":board["displayed_players"],
      "market_audit":market_audit or {"status":"not_requested"},
      "portfolio_policy":port["bankroll"],"proposed_singles":port["qualified_singles"],
      "proposed_parlays":port["qualified_parlays"],
      "official_bets":0,"settled_bets":0,
      "realized_profit":0.,"realized_roi":None,
      "no_wagers_assumed_placed":True,
      "outcome_source_not_integrated":True}
    data["audit_sha256"]=hashlib.sha256(canonical(data).encode()).hexdigest()
    return data

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--snapshot",default="snapshots/phase31/2026-week-06.json")
    parser.add_argument("--output-dir",default="output/phase35")
    parser.add_argument("--bankroll",type=float,default=DEFAULT_BANKROLL)
    parser.add_argument("--unit-percent",type=float,default=DEFAULT_UNIT_PERCENT)
    parser.add_argument("--request-live-fanduel",action="store_true")
    parser.add_argument("--region",choices=["us","us2","ca"],default="us")
    parser.add_argument("--event-id",default="")
    args=parser.parse_args()
    snap=json.loads(Path(args.snapshot).read_text());verify_snapshot(snap)
    board=research_dashboard(snap)
    port=portfolio([],args.bankroll,args.unit_percent)
    market=None
    if args.request_live_fanduel:
        try:market=live_fanduel_once(snap,os.getenv("ODDS_API_KEY"),args.region,args.event_id)
        except RuntimeError as exc:
            if str(exc)=="API returned HTTP 429":
                market={"status":"provider_rate_or_quota_limited","http_status":429,
                    "qualified_singles":0,"qualified_parlays":0}
            else:raise
    ledger=create_ledger(board,port,market)
    public={"version":VERSION,"frozen_week":snap["week"],
       "frozen_forecasts":len(snap["forecasts"]),
       "research_player_rows":board["displayed_players"],
       "status":"NO_APPROVED_WAGERS_MISSING_REAL_LINE_CALIBRATION_AND_OFFICIAL_ACTIVES",
       "fanduel_market_audit":market or {"status":"not_requested"},
       "portfolio":port,"qualified_singles":0,"qualified_parlays":0,
       "same_game_parlay_combined_prices_validated":False,
       "real_line_calibrated_probability_validated":False,
       "official_gameday_active_feed_verified":False,
       "market_quotes_exported":False}
    out=Path(args.output_dir);out.mkdir(parents=True,exist_ok=True)
    (out/"phase35_public_portfolio.json").write_text(json.dumps(public,indent=2))
    (out/"phase35_accountability_ledger.json").write_text(json.dumps(ledger,indent=2))
    message=("# GRIDIRON Phase 35 — FanDuel and staking readiness\n\n"
      f"**Frozen Week {snap['week']}:** {board['displayed_players']} research player forecasts.\n\n"
      f"**Bankroll:** ${port['bankroll']['bankroll']:.2f}; "
      f"**one unit:** ${port['bankroll']['unit_value']:.2f} "
      f"({port['bankroll']['unit_percent']}%).\n\n"
      f"**FanDuel quote audit:** {public['fanduel_market_audit']['status']}.\n\n"
      "**Singles qualified: 0 | Parlays qualified: 0 | Units allocated: 0.**\n\n"
      "Real-line calibrated probabilities, official gameday actives, and verified "
      "FanDuel parlay combined prices are not integrated. No sportsbook prices "
      "or licensed player-level quotes published.\n")
    print(message)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write(message)
if __name__=="__main__":main()
