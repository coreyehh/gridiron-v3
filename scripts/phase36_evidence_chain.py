"""Phase36 evidence provenance and empirical parlay dependence audit.

All sourced information is classified, not automatically trusted. Official player
actives and accepted FanDuel SGP prices are NOT integrated. No bet promotion.
No sportsbook calls; never put licensed prices in public artifacts.
"""
import argparse,hashlib,json,math,os
from collections import Counter
from datetime import datetime,timezone
from itertools import combinations
from pathlib import Path
from scripts.phase31_accountability import verify_snapshot,canonical
from scripts.phase35_fanduel_portfolio import bankroll_config,portfolio
from scripts.live_market import dt

VERSION="phase36-provenance-and-joint-probability-readiness-v1"
TRUST={"nfl_official_gameday":"requires_verified_fetch_and_identity",
       "third_party_injury":"context_only",
       "nflverse_roster":"identity_not_gameday_status",
       "fanduel_odds_api":"offer_price_not_accepted_parlay",
       "manual_note":"unverified"}
REQUIRED=("source_kind","source_url","retrieved_at_utc","event_id",
          "player_id","status","kickoff_utc","source_record_sha256")
STATUSES={"ACTIVE","INACTIVE","QUESTIONABLE","DOUBTFUL","OUT","UNKNOWN"}

def provenance(row,snapshot_lock=None,asof=None):
    """Strong chronological checks, but metadata alone NEVER authenticates URL."""
    reasons=[]
    if not isinstance(row,dict):return {"usable_for_official_actives":False,
           "status":"REJECTED","reasons":["invalid_evidence_record"]}
    for field in REQUIRED:
        if not row.get(field):reasons.append("missing_"+field)
    if row.get("source_kind") not in TRUST:reasons.append("unknown_source_type")
    if row.get("status") not in STATUSES:reasons.append("unsupported_status")
    url=row.get("source_url")
    if not isinstance(url,str) or not url.startswith("https://"):
        reasons.append("not_https_source")
    try:
        captured=dt(row["retrieved_at_utc"])
        kickoff=dt(row["kickoff_utc"])
        now=dt(asof) if asof else datetime.now(timezone.utc)
        if captured>now:reasons.append("future_retrieval_time")
        if captured>=kickoff:reasons.append("evidence_after_kickoff")
        if snapshot_lock and dt(snapshot_lock)>captured:
            reasons.append("evidence_predates_forecast_lock")
    except (KeyError,ValueError,TypeError):
        reasons.append("unverifiable_source_time")
    digest=row.get("source_record_sha256")
    if not isinstance(digest,str) or len(digest)!=64 or any(x not in "0123456789abcdef" for x in digest):
        reasons.append("invalid_source_record_digest")
    # A fabricated source URL and hash can trivially be submitted by caller;
    # require independent server-side fetch/attestation, not supplied booleans.
    reasons.append("source_authenticity_not_independently_attested")
    return {"usable_for_official_actives":False,
      "status":"REJECTED" if len(reasons)>1 else "PROVENANCE_ONLY",
      "reasons":sorted(set(reasons)),
      "source_kind":row.get("source_kind","UNKNOWN")}

def paired_binary_dependence(samples,min_weeks=6,min_pairs=150):
    """Research P(A,B), conditional frequencies, uncertainty diagnostics.

    Samples require *same historical game scenario* paired observations.
    No independence assumption, no sportsbook pricing and no deployable parlay.
    """
    if not isinstance(samples,list):raise ValueError("Expected paired outcomes")
    checked=[];weeks=set()
    for r in samples:
        if not isinstance(r,dict) or not isinstance(r.get("week"),int) or r.get("week")<1:
            raise ValueError("Week provenance missing")
        a,b=r.get("a"),r.get("b")
        if type(a) is not bool or type(b) is not bool:
            raise ValueError("Must supply two observed binary outcomes")
        if not r.get("historical_fixture_id"):raise ValueError("Fixture linkage missing")
        checked.append((a,b));weeks.add(r["week"])
    n=len(checked)
    count_a=sum(a for a,b in checked);count_b=sum(b for a,b in checked)
    count_both=sum(a and b for a,b in checked)
    status="INSUFFICIENT_INDEPENDENT_EVIDENCE" if n<min_pairs or len(weeks)<min_weeks else "DESCRIPTIVE_DEPENDENCE_ONLY"
    return {"status":status,"observations":n,"distinct_weeks":len(weeks),
      "both_hit_n":count_both,"a_hit_rate":round(count_a/n,5) if n else None,
      "b_hit_rate":round(count_b/n,5) if n else None,
      "joint_hit_rate":round(count_both/n,5) if n else None,
      "p_b_given_a":round(count_both/count_a,5) if count_a else None,
      "independence_baseline":round((count_a/n)*(count_b/n),5) if n else None,
      "not_out_of_sample_calibrated":True,
      "market_price_and_combined_payout_verified":False,
      "qualified_parlays":0}

def freeze_private_quote_hash(quotes,created_at_utc,output_path=None):
    """Commitment hash only. Never persist raw licensed rows or key on GitHub.

    A local private path can retain a per-quote digest (no player, book, price,
    event or lines). Hash has limited audit utility absent private originals.
    """
    at=dt(created_at_utc)
    if not isinstance(quotes,list):raise ValueError("Quotes must be a list")
    records=[]
    for r in quotes:
        if not isinstance(r,dict) or r.get("bookmaker")!="fanduel":
            raise ValueError("Only FanDuel source rows permitted")
        if dt(r["captured_at_utc"])>at or dt(r["captured_at_utc"])>=dt(r["kickoff_utc"]):
            raise ValueError("Future or postkickoff quote")
        records.append(hashlib.sha256(canonical(r).encode()).hexdigest())
    result={"status":"volatile_quote_digest_only","quote_count":len(records),
        "capture_utc":created_at_utc,
        "root_sha256":hashlib.sha256(canonical(records).encode()).hexdigest(),
        "raw_quotes_retained":False,"player_prices_exported":False,
        "proof_of_provider_origin":False,"verified_fanduel_sgp_quotes":False}
    if output_path:
        dest=Path(output_path)
        if "private_data" not in dest.parts:raise ValueError("Must write under private_data")
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(json.dumps(result,indent=2))
        os.chmod(dest,0o600)
    return result

def phase36(snapshot,bankroll=1000.,unit_pct=1.,evidence=None):
    verify_snapshot(snapshot)
    gate=bankroll_config(bankroll,unit_pct)
    audits=[provenance(r,snapshot_lock=snapshot["created_at_utc"].replace("+00:00","Z"))
           for r in (evidence or [])]
    # No authenticated official source exists yet. Never use caller-supplied
    # status, probability or joint-price fields to qualify bets.
    status_counts=Counter(a["status"] for a in audits)
    demo=paired_binary_dependence([])
    result={"version":VERSION,"week":snapshot["week"],
        "forecast_snapshot_sha256":snapshot["payload_sha256"],
        "frozen_forecasts":len(snapshot["forecasts"]),
        "fixture_count":len(snapshot["fixtures"]),
        "evidence_manifest_records":len(audits),
        "evidence_status_counts":dict(status_counts),
        "official_game_day_active_records_authenticated":0,
        "independent_real_fanduel_line_calibration_passed":False,
        "empirical_joint_outcome_validation_passed":False,
        "fanduel_accepted_sgp_combined_price_integrated":False,
        "paired_dependence_research":demo,
        "bankroll":gate,"portfolio":portfolio([],bankroll,unit_pct),
        "qualified_singles":0,"qualified_2_to_5_leg_parlays":0,
        "allocated_units":0,
        "decision":"NO_BETS_EVIDENCE_INCOMPLETE"}
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--snapshot",default="snapshots/phase31/2026-week-06.json")
    p.add_argument("--output",default="output/phase36_evidence_chain.json")
    p.add_argument("--bankroll",type=float,default=1000.)
    p.add_argument("--unit-percent",type=float,default=1.)
    a=p.parse_args()
    snapshot=json.loads(Path(a.snapshot).read_text())
    r=phase36(snapshot,a.bankroll,a.unit_percent)
    path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(r,indent=2))
    report=("# GRIDIRON Phase36 — Evidence and parlay dependency readiness\n\n"
      f"**Frozen predictions:** {r['frozen_forecasts']} across {r['fixture_count']} games.\n\n"
      f"**Bankroll:** ${r['bankroll']['bankroll']:.2f}; "
      f"**unit size:** ${r['bankroll']['unit_value']:.2f}.\n\n"
      "**Official active records authenticated:** 0.\n\n"
      "**Verified FanDuel same-game combined parlay prices:** 0.\n\n"
      "**Real-line probabilities independently calibrated:** No.\n\n"
      "**Qualified singles: 0 | 2–5-leg parlays: 0 | Units: 0.**\n\n"
      "No sports-odds API calls, quote exports or fabricated picks.\n")
    print(report)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write(report)
if __name__=="__main__":main()
