"""GRIDIRON Phase42 — multi-market FanDuel expansion, research-only.

Adds pass, rush, TD (including 2+ and 3+ scoring price discovery).
The 2026 Week6 Phase31 frozen model forecasts receptions and receiving yards
ONLY. Never fill other market projections from market prices or zeroes.
"""
import argparse,hashlib,json,math,os
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from cryptography.fernet import Fernet
from scripts.phase31_accountability import verify_snapshot,canonical
from scripts.phase39_secure_quote_evidence import decrypt_archive,verify_cipher_key
from scripts.phase41_full_slate import inspect_import
from scripts.phase32_market_matching import discover,selected_fixture,matched_forecasts
from scripts.phase28_snap_participation import name_key
from scripts.live_market import dt,implied
from scripts.live_odds_smoke import SPORT,fetch_json

VERSION="phase42-pass-rush-touchdown-coverage-v1"
# Odds API NFL player market identifiers. Provider/book coverage is variable.
CATEGORIES={
 "passing":{"player_pass_yds":"passing_yards",
            "player_pass_attempts":"pass_attempts",
            "player_pass_completions":"completions",
            "player_pass_interceptions":"interceptions",
            "player_pass_tds":"passing_touchdowns"},
 "rushing":{"player_rush_yds":"rushing_yards",
            "player_rush_attempts":"rush_attempts"},
 "touchdowns":{"player_anytime_td":"anytime_touchdown",
               "player_1st_td":"first_touchdown",
               "player_2plus_tds":"two_plus_touchdowns",
               "player_3plus_tds":"three_plus_touchdowns"}
}
LOOKUP={k:(cat,v) for cat,markets in CATEGORIES.items() for k,v in markets.items()}
BINARY=set(CATEGORIES["touchdowns"].values())
MAX_EVENTS=13
MAX_ROWS=16000

def supported(categories):
    if not isinstance(categories,(list,tuple)) or not categories:raise ValueError("Choose at least one category")
    if len(categories)!=len(set(categories)) or any(c not in CATEGORIES for c in categories):
        raise ValueError("Unsupported or duplicate category")
    return tuple(k for c in categories for k in CATEGORIES[c])

def player_of(outcome, market):
    """A TD player is often outcome.name, with no description/point."""
    label=str(outcome.get("name","")).strip()
    desc=str(outcome.get("description") or "").strip()
    if market in BINARY:
        if label.lower() in ("yes","no"):
            if not desc:return None,None
            return desc,label.lower()
        if label.lower() in ("over","under"):return None,None
        if desc and desc!=label:return None,None
        return label,"yes"
    if label.lower() not in ("over","under") or not desc:return None,None
    return desc,label.lower()

def extract(payload,captured,snapshot,event):
    """Parse real FanDuel quotes only; reject mixed kickoff/event after lock."""
    verify_snapshot(snapshot)
    fixture=selected_fixture(snapshot,event)
    if any(payload.get(k)!=event.get(k) for k in ("id","commence_time","home_team","away_team")):
        raise ValueError("Bookmaker event identity differs from discovery")
    cap=dt(captured);kick=dt(event["commence_time"])
    lock=dt(snapshot["created_at_utc"].replace("+00:00","Z"))
    if not lock<cap<kick:raise ValueError("Capture was not post-lock pregame")
    booklist=payload.get("bookmakers")
    if not isinstance(booklist,list) or any(b.get("key")!="fanduel" for b in booklist):
        raise ValueError("Not FanDuel-only response")
    known,_=matched_forecasts(snapshot,fixture)
    rows=[];counts=Counter();seen=set()
    for book in booklist:
        for market in book.get("markets",[]):
            key=market.get("key")
            if key not in LOOKUP:continue
            category,metric=LOOKUP[key]
            quote_time=market.get("last_update") or book.get("last_update")
            q=dt(quote_time)
            if q<lock or q>cap or q>=kick or (cap-q).total_seconds()>3600:
                counts["stale_or_prelock_markets"]+=1;continue
            for o in market.get("outcomes",[]):
                counts["raw_outcomes"]+=1
                player,side=player_of(o,metric)
                if not player or not side:
                    counts["unsupported_shape"]+=1;continue
                try:
                    odds=o["price"];implied(odds)
                    point=None if metric in BINARY else float(o["point"])
                    if point is not None and (not math.isfinite(point) or point<0):continue
                    if metric in BINARY and o.get("point") is not None:
                        counts["invalid_td_points"]+=1;continue
                except (ValueError,TypeError,KeyError):
                    counts["bad_price_or_line"]+=1;continue
                named=known.get(name_key(player))
                if named is None:
                    counts["not_unique_name_match"]+=1;continue
                marker=(named["player_id"],metric,side,point)
                if marker in seen:
                    counts["duplicate_outcome"]+=1;continue
                seen.add(marker)
                # The frozen snapshot has NO QB, rush or TD forecasts.
                # Even a normal source identity match does not establish GSIS provider ID.
                rows.append({"fixture_id":fixture["id"],"event_id":event["id"],
                  "player_id":named["player_id"],"player_name":named["player_name"],
                  "team":named["team"],"category":category,"market":metric,
                  "side":side,"fanduel_line":point,"american_odds":int(odds),
                  "capture_utc":captured,"book_updated_utc":quote_time,
                  "kickoff_utc":event["commence_time"],
                  "player_identity_provider_verified":False,
                  "projection":None,"projection_status":"NOT_MODELED_IN_FROZEN_SNAPSHOT",
                  "model_probability":None,"two_plus_td_probability":None,
                  "three_plus_td_probability":None,"estimated_ev":None,
                  "game_day_active_verified":False,"qualified":False,
                  "wager_placed":False,"units":0})
                counts["accepted_outcome_sides"]+=1
    if len(rows)>MAX_ROWS:raise ValueError("Unbounded quote rows")
    return rows,{"fixture_id":fixture["id"],"counts":dict(counts)}

def strict_groups(rows):
    """Keep paired pass/rush markets and authentic one-sided TD evidence.

    No synthetic No odds for touchdown market; do not infer negative-side prices.
    """
    paired=defaultdict(list);td=[];rejected=Counter()
    for row in rows:
        if row["category"]=="touchdowns":
            if row["side"]=="yes":td.append(row)
            else:rejected["unpaired_binary_no_side"]+=1
        else:
            paired[(row["fixture_id"],row["player_id"],row["market"],row["fanduel_line"])].append(row)
    results=list(td)
    for pair in paired.values():
        if len(pair)!=2 or {x["side"] for x in pair}!={"over","under"}:
            rejected["missing_or_ambiguous_two_sided_market"]+=1;continue
        if pair[0]["book_updated_utc"]!=pair[1]["book_updated_utc"]:
            rejected["timestamp_mismatch"]+=1;continue
        p=sum(implied(x["american_odds"]) for x in pair)
        if not .99<=p<=1.40:
            rejected["invalid_hold"]+=1;continue
        results.extend(pair)
    return results,dict(rejected)

def merge(snapshot,older,new):
    verify_snapshot(snapshot)
    existing=older.get("entries",[]) if older else []
    if older and older["frozen_snapshot_sha256"]!=snapshot["payload_sha256"]:
        raise ValueError("Cannot combine different forecast freezes")
    fixture_ids={f["id"] for f in snapshot["fixtures"]}
    if any(r["fixture_id"] not in fixture_ids for r in new):raise ValueError("Unknown fixture")
    # Preserve ALL prior Phase41 quotes untouched in an embedded section.
    # Do not silently mix incompatible schema or rewrite earlier forecasts.
    records={"version":VERSION,"snapshot_sha256":snapshot["payload_sha256"],
       "season":snapshot["season"],"week":snapshot["week"],
       "original_receiving_entries":existing,
       "new_market_quotes":new,"prior_receiving_pairs":len(existing),
       "expanded_quote_sides":len(new),
       "categories":list(CATEGORIES),"qualified_bets":0,"allocated_units":0,
       "model_validated_new_market_probabilities":False,
       "not_yet_modeled":["passing","rushing","touchdowns"],
       "purpose":"PRIVATE_HISTORICAL_RESEARCH_NOT_PICKS"}
    return records

def audit(snapshot,prior=None,live=False,max_events=0,categories=("passing","rushing","touchdowns"),key=None,
          region="us",odds_key=None,discover_fn=discover,fetch_fn=fetch_json):
    verify_snapshot(snapshot)
    markets=supported(categories)
    if max_events<0 or max_events>MAX_EVENTS:raise ValueError("Event limit outside 0-13")
    if region not in ("us","us2","ca"):raise ValueError("Invalid region")
    summaries=[];all_new=[];attempts=0;seen=set()
    if live:
        verify_cipher_key(key)
        if not odds_key or max_events==0:raise ValueError("Paid collection requires API key and positive event cap")
        for event in discover_fn(odds_key,snapshot):
            if attempts>=max_events:break
            if event["id"] in seen:continue
            seen.add(event["id"])
            if dt(event["commence_time"])<=datetime.now(timezone.utc):continue
            selected_fixture(snapshot,event)
            if dt(event["commence_time"])<=datetime.now(timezone.utc):continue
            attempts+=1
            try:
                payload,_=fetch_fn("/v4/sports/"+SPORT+"/events/"+event["id"]+"/odds",
                    {"regions":region,"markets":",".join(markets),
                    "bookmakers":"fanduel","oddsFormat":"american"},odds_key)
                stamp=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
                rows,diag=extract(payload,stamp,snapshot,event)
                kept,rej=strict_groups(rows)
                all_new.extend(kept)
                summaries.append({"fixture_id":diag["fixture_id"],
                    "accepted_sides":len(kept),"rejections":rej})
            except (RuntimeError,ValueError,KeyError,TypeError) as e:
                summaries.append({"status":"PROVIDER_OR_VALIDATION_REJECTED"})
                if str(e)=="API returned HTTP 429":break
    combined=merge(snapshot,prior,all_new)
    safe={"version":VERSION,"snapshot_fixtures":len(snapshot["fixtures"]),
      "snap_forecast_count":len(snapshot["forecasts"]),
      "previous_receiving_market_pairs":len(prior["entries"]) if prior else 0,
      "new_pass_rush_td_quote_sides":len(all_new),
      "new_event_quote_requests":attempts,"events":summaries,
      "new_market_projection_available":False,"player_identity_verified":False,
      "official_bets":0,"units":0,"licensed_prices_in_public":False}
    return combined,safe

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--snapshot",default="snapshots/phase31/2026-week-06.json")
    p.add_argument("--prior-archive",default="")
    p.add_argument("--live",action="store_true")
    p.add_argument("--event-cap",type=int,default=0)
    p.add_argument("--categories",nargs="+",choices=tuple(CATEGORIES),default=list(CATEGORIES))
    p.add_argument("--region",choices=("us","us2","ca"),default="us")
    p.add_argument("--output-dir",default="output/phase42")
    a=p.parse_args()
    snapshot=json.loads(Path(a.snapshot).read_text());verify_snapshot(snapshot)
    key=os.environ.get("QUOTE_ARCHIVE_KEY");older=None
    if a.prior_archive:
        verify_cipher_key(key)
        older=inspect_import(Path(a.prior_archive).read_bytes(),key,snapshot)
    if a.live:verify_cipher_key(key)
    result,safe=audit(snapshot,older,live=a.live,max_events=a.event_cap,
       categories=a.categories,key=key,region=a.region,odds_key=os.getenv("ODDS_API_KEY"))
    out=Path(a.output_dir);out.mkdir(parents=True,exist_ok=True)
    if a.prior_archive or a.live:
        cipher=Fernet(verify_cipher_key(key)).encrypt(canonical(result).encode())
        dest=out/"expanded_private_market_archive.fernet"
        dest.write_bytes(cipher);os.chmod(dest,0o600)
        safe["encrypted_archive_sha256"]=hashlib.sha256(cipher).hexdigest()
    (out/"public_summary.json").write_text(json.dumps(safe,indent=2))
    msg=(f"# GRIDIRON Phase42 — pass, rush & touchdown market coverage\n\n"
       f"**Existing receiving pairs preserved:** {safe['previous_receiving_market_pairs']}.\n\n"
       f"**New quote sides archived:** {safe['new_pass_rush_td_quote_sides']}; "
       f"**additional paid event requests:** {safe['new_event_quote_requests']}.\n\n"
       "**No new-market calibrated projections, qualified bets or units.**\n")
    print(msg)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write(msg)
if __name__=="__main__":main()
