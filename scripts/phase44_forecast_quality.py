"""GRIDIRON Phase44: forecast QA + time-honest private market comparison.

Preserves immutable Week6 model and Phase41 offer records without fabricating
official player actives, lineup roles, EV, or prospectively valid picks.
"""
import argparse,json,math,os,hashlib
from collections import Counter,defaultdict
from pathlib import Path
from cryptography.fernet import Fernet
from scripts.phase43_remaining_week6 import check_remaining
from scripts.phase39_secure_quote_evidence import decrypt_archive,verify_cipher_key
from scripts.phase31_accountability import canonical
from scripts.phase28_snap_participation import name_key
from scripts.live_market import dt

VERSION="phase44-forecast-role-audit-and-private-time-integrity-v1"
PASS=("passing_yards","pass_attempts","completions","interceptions","passing_touchdowns")
RUSH=("rushing_yards","rush_attempts")
TD=("anytime_touchdown","two_plus_touchdowns","three_plus_touchdowns")
# Heuristic "needs scrutiny" thresholds, not scientific cutoffs.
HIGH_PASS_YDS=350
HIGH_RUSH_YDS=100
HIGH_CARRIES=22

def quality(row):
    """Readable explanation of heuristic risks. Neither team nor position proves lineup."""
    p=row["point_projections"];pos=row["position"]
    reasons=["OFFICIAL_ACTIVE_STATUS_NOT_VERIFIED","CURRENT_WEEK_ROLE_NOT_VERIFIED",
             "PROVISIONAL_NOT_LINE_CALIBRATED"]
    if pos in ("RB","WR","TE") and (p.get("passing_yards") or 0)>30:
        reasons.append("UNUSUAL_NON_QB_PASSING_VOLUME")
    if pos in ("WR","TE") and (p.get("rush_attempts") or 0)>5:
        reasons.append("UNUSUAL_RECEIVER_CARRIES")
    if pos=="QB" and (p.get("pass_attempts") or 0)<15:
        reasons.append("LOW_QB_PASSING_SAMPLE_OR_ROLE")
    if (p.get("passing_yards") or 0)>HIGH_PASS_YDS:
        reasons.append("EXTREME_PASSING_YARDS_ESTIMATE")
    if (p.get("rushing_yards") or 0)>HIGH_RUSH_YDS:
        reasons.append("EXTREME_RUSHING_YARDS_ESTIMATE")
    if (p.get("rush_attempts") or 0)>HIGH_CARRIES:
        reasons.append("EXTREME_RUSHING_WORKLOAD")
    # Deterministic mean-only touchdown models can manufacture spurious
    # 0% outcomes. Do not interpret mean==0 as verified zero probability.
    if p.get("td_count_mean")==0:
        reasons.append("ZERO_OBSERVED_TD_RATE_NOT_ZERO_TRUE_CHANCE")
    if row.get("observed_player_games",0)<5:
        reasons.append("LIMITED_PLAYER_HISTORY")
    return {"fixture_id":row["fixture_id"],"player_name":row["player_name"],
      "team":row["team"],"position":pos,"player_id":row["player_id"],
      "point_projections":p,"risk_reasons":sorted(set(reasons)),
      "risk_flags":len(reasons)-3,"availability_verified":False,
      "bet_qualified":False,"stake_units":0,
      "decision":"HOLD_RESEARCH_ONLY"}

def audit(snapshot):
    check_remaining(snapshot)
    rows=[quality(x) for x in snapshot["forecasts"]]
    stats=Counter()
    for x in rows:
        for reason in x["risk_reasons"]:stats[reason]+=1
    return rows,{"version":VERSION,"week":snapshot["week"],
      "snapshot_sha256":snapshot["payload_sha256"],"fixtures":len(snapshot["fixtures"]),
      "player_forecasts":len(rows),"flags":dict(sorted(stats.items())),
      "official_player_active_verified":False,"roles_verified":False,
      "qualified_bets":0,"units":0,"calibrated_ev_available":False}

def require_ledger(ledger):
    chk=ledger.get("lock_sha256")
    if not chk or hashlib.sha256(canonical({k:v for k,v in ledger.items()
                                             if k!="lock_sha256"}).encode()).hexdigest()!=chk:
        raise ValueError("Phase41 encrypted ledger integrity mismatch")
    if ledger.get("official_bets")!=0:raise ValueError("Unexpected wager state")
    if not isinstance(ledger.get("entries"),list):raise ValueError("Missing entries")
    return True

def private_compare(snapshot,ledger):
    """Exact fixture/team + unique normalized name, historical receiving only.

    Earliest valid prospective odds require a MODEL freeze before the bookmaker
    quote's own update time, not only before API archive capture.
    """
    check_remaining(snapshot);require_ledger(ledger)
    byname=defaultdict(list)
    for r in snapshot["forecasts"]:
        byname[(r["fixture_id"],r["team"],name_key(r["player_name"]))].append(r)
    output=[];stats=Counter()
    snapshot_at=dt(snapshot["created_at_utc"])
    for offer in ledger["entries"]:
        if offer.get("market") not in ("receptions","receiving_yards"):
            stats["unsupported_market"]+=1;continue
        iden=(offer["fixture_id"],offer["team"],name_key(offer["player_name"]))
        found=byname.get(iden,[])
        if len(found)!=1:
            stats["missing_or_ambiguous_player"]+=1;continue
        player=found[0]
        # Phase43 does not model receiving metrics, so it CANNOT fill them.
        # The original Phase31 receiving number in the ledger was locked earlier
        # and belongs to another model; keep it separate and unchanged.
        quote_time=dt(offer["over_quote_updated_utc"])
        quote2=dt(offer["under_quote_updated_utc"])
        prequote=snapshot_at<=min(quote_time,quote2)
        # The model has no receiving_yards/receptions prediction.
        stats["matches_between_separate_model_families"]+=1
        stats["phase43_lock_after_original_market_quote" if not prequote else
              "phase43_lock_before_market_quote"]+=1
        output.append({"fixture_id":offer["fixture_id"],
           "player_name":player["player_name"],"team":player["team"],
           "market":offer["market"],"fanduel_line":offer["fanduel_line"],
           "over_american_odds":offer["over_american_odds"],
           "under_american_odds":offer["under_american_odds"],
           "phase31_original_receiving_forecast":offer["frozen_projection"],
           "phase43_new_market_forecast":None,
           "phase43_lock_before_bookmaker_quote":prequote,
           "phase43_quote_comparison_eligible":False,
           "prospective_edge":None,"estimated_ev":None,
           "decision":"NO_PHASE43_RECEIVING_FORECAST",
           "qualified_bet":False,"stake_units":0})
    return output,dict(stats)

def run(snapshot,ledger=None):
    qa,public=audit(snapshot)
    comparison=[];stats={}
    if ledger is not None:comparison,stats=private_compare(snapshot,ledger)
    public["comparison"]={"real_paired_quotes_examined":len(ledger["entries"]) if ledger else 0,
      "same_player_fixture_identity_matches":len(comparison),
      "timing_and_family_counts":stats,
      "phase43_sportsbook_edges_qualified":0,
      "individual_fanduel_prices_in_public":False}
    return qa,comparison,public

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--snapshot",default="snapshots/phase43/remaining/2026-week-06-remaining-20261018T162430Z.json")
    p.add_argument("--encrypted-phase41",default="")
    p.add_argument("--output-dir",default="output/phase44")
    a=p.parse_args()
    snap=json.loads(Path(a.snapshot).read_text())
    ledger=None;key=os.environ.get("QUOTE_ARCHIVE_KEY")
    if a.encrypted_phase41:
        ledger=decrypt_archive(Path(a.encrypted_phase41).read_bytes(),key)
    qa,comparison,public=run(snap,ledger)
    out=Path(a.output_dir);out.mkdir(exist_ok=True,parents=True)
    # All forecast-based QA can be readable/public. No bookstore quote columns.
    import csv
    with (out/"forecast_quality_review.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["fixture_id","player_name","team","position",
             "risk_flags","risk_reasons","passing_yards","pass_attempts",
             "rushing_yards","rush_attempts","anytime_td_unvalidated",
             "two_plus_td_unvalidated","three_plus_td_unvalidated","decision"])
        w.writeheader()
        for x in qa:
            pp=x["point_projections"]
            w.writerow({"fixture_id":x["fixture_id"],"player_name":x["player_name"],
              "team":x["team"],"position":x["position"],
              "risk_flags":x["risk_flags"],"risk_reasons":"; ".join(x["risk_reasons"]),
              "passing_yards":pp.get("passing_yards"),
              "pass_attempts":pp.get("pass_attempts"),
              "rushing_yards":pp.get("rushing_yards"),"rush_attempts":pp.get("rush_attempts"),
              "anytime_td_unvalidated":pp.get("anytime_touchdown"),
              "two_plus_td_unvalidated":pp.get("two_plus_touchdowns"),
              "three_plus_td_unvalidated":pp.get("three_plus_touchdowns"),
              "decision":x["decision"]})
    if ledger is not None:
        crypt=Fernet(verify_cipher_key(key)).encrypt(canonical({
          "version":VERSION,"phase43_snapshot_hash":snap["payload_sha256"],
          "prior_phase41_lock_hash":ledger["lock_sha256"],
          "research_comparison":comparison,"no_approved_picks":True}).encode())
        dest=out/"private_market_reconciliation.fernet"
        dest.write_bytes(crypt);os.chmod(dest,0o600)
        public["comparison"]["encrypted_private_report_sha256"]=hashlib.sha256(crypt).hexdigest()
    (out/"public_summary.json").write_text(json.dumps(public,indent=2))
    msg=(f"# Phase44 — Projection quality audit\n\n"
         f"**Players audited:** {public['player_forecasts']}; **fixtures:** {public['fixtures']}.\n\n"
         f"**Verified bets:** 0. **Phase43 modeled receiving market matches:** 0.\n\n"
         f"**Private reconciliation rows:** {len(comparison)}; API requests: 0.\n\n"
         "Heuristic flags and new-market forecast prices are not +EV proof.\n")
    print(msg)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write(msg)
if __name__=="__main__":main()
