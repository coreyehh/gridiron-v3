"""Phase38: official NFL inactive source audit + independently scored probability gates.

Authenticated HTTPS retrieval of NFL.com inactives proves what bytes were
obtained at a given time. It DOES NOT prove a player active unless a verified,
fixture-specific inactive roster can be parsed and bound to GSIS identity.
Historical threshold research uses Phase33's strictly prior-week calibration;
no historical FanDuel offered-line dataset is present. Fail closed.
"""
import argparse,hashlib,json,os,ssl
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from scripts.phase31_accountability import verify_snapshot
from scripts.phase33_probability_evidence import prequential,MIN_INDEPENDENT_WEEKS,MIN_PROB_CASES
from scripts.phase35_fanduel_portfolio import bankroll_config
from scripts.live_market import dt

VERSION="phase38-official-source-and-prospective-calibration-gate-v1"
OFFICIAL_URL="https://www.nfl.com/inactives/"
REQUIRED_MARKETS=("receptions","receiving_yards")

def official_page_probe(fetcher=None,now=None):
    """Official-host HTTPS TLS validated evidence, never active/inactive names."""
    at=now or datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    dt(at)
    report={"official_url":OFFICIAL_URL,"retrieved_at_utc":at,
        "source_kind":"nfl_official_public_inactives_page",
        "https_certificate_validation_required":True,
        "source_reachable":False,"http_status":None,"raw_content_sha256":None,
        "bytes_received":0,"validated_fixture_bound_gsis_inactive_entries":0,
        "official_active_status_verified":False,
        "player_game_inactives_attested":False,
        "reason":"no_verified_fixture_player_inactive_parser"}
    try:
        if fetcher is None:
            req=Request(OFFICIAL_URL,headers={"User-Agent":"GRIDIRON-research/1.0"})
            with urlopen(req,timeout=12,context=ssl.create_default_context()) as resp:
                url=resp.geturl()
                if urlparse(url).scheme!="https" or urlparse(url).hostname!="www.nfl.com":
                    raise ValueError("Official source redirected outside approved HTTPS origin")
                content=resp.read(2_000_001)
                status=resp.status
        else:
            # Tests inject a transport. Never trust a caller-supplied status as
            # player evidence: only record source bytes, not extracted names.
            status,content,url=fetcher(OFFICIAL_URL)
            if urlparse(url).scheme!="https" or urlparse(url).hostname!="www.nfl.com":
                raise ValueError("Invalid source origin")
        if not isinstance(content,bytes) or len(content)>2_000_000:
            raise ValueError("Invalid or oversized source response")
        report["http_status"]=int(status)
        if int(status)!=200:raise ValueError("Official page was not HTTP 200")
        if not content:raise ValueError("Empty official page")
        report["source_reachable"]=True
        report["raw_content_sha256"]=hashlib.sha256(content).hexdigest()
        report["bytes_received"]=len(content)
    except HTTPError as err:
        report["http_status"]=err.code
        report["reason"]="official_source_http_error"
    except (URLError,TimeoutError,OSError,ValueError,TypeError) as err:
        report["reason"]="official_source_unavailable_or_not_authenticated"
    return report

def evaluated_week_diagnostics(report):
    """Separate thresholds from independently scored weeks and observed boxes."""
    scores=report["scores"];markets={}
    for market in REQUIRED_MARKETS:
        s=scores[market]
        markets[market]={"threshold_outcomes_scored":s["cases"],
            "independent_scored_weeks":len(s["weeks"]),
            "scored_week_ids":s["weeks"],
            "brier":s["brier"],"expected_calibration_error":s["ece"],
            "preliminary_week_gate_pass":len(s["weeks"])>=MIN_INDEPENDENT_WEEKS,
            "preliminary_threshold_count_gate_pass":s["cases"]>=MIN_PROB_CASES,
            "offered_line_observations":0,
            "fanduel_specific_line_probabilities_validated":False}
    return {"markets":markets,"observed_player_game_rows":report["observed_player_games"],
        "missing_box_rows_not_assumed_zero":report["missing_box_rows_excluded"],
        "all_thresholds_predefined_illustrative_not_fanduel":True,
        "in_sample_base_rate_not_valid_out_of_sample_benchmark":True,
        "prospective_real_fanduel_line_validation_pass":False,
        "qualified_market_probabilities":0}

def prospective_offer_gate(records,min_weeks=MIN_INDEPENDENT_WEEKS,min_player_games=1500):
    """Score prospective, pre-recorded FanDuel outcome observations only.

    The record format supports future authorized private evidence imports, but
    caller-supplied booleans DO NOT authenticate archived provider quotes.
    Even favorable Brier scores cannot bypass provider proof and active gates.
    """
    if not isinstance(records,list):raise ValueError("Offer evidence must be list")
    counts=defaultdict(int);weeks=set();games=set();flags=[]
    for r in records:
        if not isinstance(r,dict):raise ValueError("Bad archived record")
        for k in ("week","fixture_id","player_id","market","line","quoted_at_utc",
                  "captured_at_utc","kickoff_utc","outcome","frozen_probability"):
            if k not in r:raise ValueError("Missing archived field: "+k)
        if r["market"] not in REQUIRED_MARKETS:raise ValueError("Unsupported market")
        from scripts.phase35_fanduel_portfolio import finite_amount
        if type(r["outcome"]) is not int or r["outcome"] not in (0,1):
            raise ValueError("Outcome must be 0 or 1, never missing-to-zero")
        if isinstance(r["week"],bool) or not isinstance(r["week"],int) or r["week"]<1:
            raise ValueError("Invalid week")
        line=finite_amount(r["line"],"line")
        p=finite_amount(r["frozen_probability"],"probability")
        if p>1:raise ValueError("Probability exceeds one")
        t=dt(r["quoted_at_utc"]);c=dt(r["captured_at_utc"]);k=dt(r["kickoff_utc"])
        if not t<=c<k:raise ValueError("Lookahead or postgame offer")
        if r.get("bookmaker")!="fanduel":raise ValueError("Not FanDuel")
        key=(r["fixture_id"],r["player_id"],r["market"],line)
        if key in games:raise ValueError("Duplicate real-line outcome")
        games.add(key);weeks.add(r["week"]);counts[r["market"]]+=1
        flags.append((p-r["outcome"])**2)
    # IMPORTANT: supplied 'source_authenticated: true' is not a source attestation.
    # Only a future independent authorized fetch + retained private snapshot can
    # pass the attestation and actual-offer calibration gate.
    return {"source_attestation_integrated":False,
        "observed_real_line_records_supplied":len(records),
        "independent_weeks":len(weeks),
        "distinct_player_market_fixture_rows":len(games),
        "mean_brier_on_supplied_records":round(sum(flags)/len(flags),5) if flags else None,
        "research_volume_sufficient":len(weeks)>=min_weeks and len(games)>=min_player_games,
        "provider_authenticated_offer_archive_available":False,
        "prospective_fanduel_probability_calibration_verified":False,
        "official_availability_verified":False,"qualified_singles":0}

def build(snapshot,calibration=None,official=None,bankroll=1000,unit_percent=1):
    verify_snapshot(snapshot)
    cfg=bankroll_config(bankroll,unit_percent)
    if calibration is None:
        evidence={"status":"not_run","prospective_real_fanduel_line_validation_pass":False}
    else:
        evidence=evaluated_week_diagnostics(calibration)
    return {"version":VERSION,"season":snapshot["season"],"week":snapshot["week"],
        "immutable_snapshot_sha256":snapshot["payload_sha256"],
        "frozen_forecast_rows":len(snapshot["forecasts"]),
        "fixture_count":len(snapshot["fixtures"]),
        "official_inactives_page_audit":official or
            {"status":"not_requested","official_active_status_verified":False},
        "historical_probability_evidence":evidence,
        "actual_book_line_audit":prospective_offer_gate([]),
        "units":cfg,"qualified_singles":0,
        "qualified_parlays_by_leg_count":{str(n):0 for n in range(2,6)},
        "units_allocated":0,
        "decision":"PASS_NO_VALIDATED_INACTIVES_OR_REAL_LINE_PROBABILITIES"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--snapshot",default="snapshots/phase31/2026-week-06.json")
    p.add_argument("--run-real-history",action="store_true")
    p.add_argument("--probe-official-nfl",action="store_true")
    p.add_argument("--bankroll",type=float,default=1000)
    p.add_argument("--unit-percent",type=float,default=1)
    p.add_argument("--output",default="output/phase38_official_and_calibration.json")
    a=p.parse_args()
    snapshot=json.loads(Path(a.snapshot).read_text())
    calib=None
    if a.run_real_history:
        import pandas as pd
        from scripts.phase18 import fetch_schedule
        from scripts.ingest import download
        store=Path("private_data");store.mkdir(exist_ok=True)
        schedule,_=fetch_schedule(store)
        frames=[download(year,store)[0] for year in (2025,2026)]
        calib=prequential(pd.concat(frames,ignore_index=True),schedule,4,18)
    official=official_page_probe() if a.probe_official_nfl else None
    result=build(snapshot,calib,official,a.bankroll,a.unit_percent)
    dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,indent=2))
    h=result["historical_probability_evidence"]
    report=(f"# GRIDIRON Phase38 — Actual evidence audit\n\n"
        f"**Frozen Week {result['week']}:** {result['frozen_forecast_rows']} forecasts, "
        f"{result['fixture_count']} games.\n\n")
    if "markets" in h:
        for market,m in h["markets"].items():
            report+=f"- {market}: {m['threshold_outcomes_scored']} illustrative threshold outcomes across {m['independent_scored_weeks']} independently scored weeks. Brier: {m['brier']}.\n"
    else:report+="- Historical validation was not requested.\n"
    source=result["official_inactives_page_audit"]
    report+=(f"\n**Official NFL inactives page:** {'HTTPS source fetched' if source.get('source_reachable') else source.get('status',source.get('reason'))}. "
       "**Player-level official active confirmation: 0.**\n\n"
       "**Actual FanDuel line-calibrated probabilities: 0.**\n\n"
       "**Qualified singles/parlays: 0; allocated units: 0.**\n\n"
       "Official page content is NOT equivalent to verified fixture/player active statuses. "
       "No paid sportsbook requests or player-level licensed quotes.\n")
    print(report)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as file:file.write(report)
if __name__=="__main__":main()
