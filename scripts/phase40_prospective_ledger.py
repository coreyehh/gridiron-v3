"""GRIDIRON Phase 40 — prospective FanDuel quote/forecast ledger and settlement.

A Phase39 Fernet ciphertext is read and authenticated in memory. Match exact
frozen fixture and unique normalized player name (unverified provider GSIS ID).
Output ONLY newly encrypted ledger plus anonymized aggregate diagnostics.
No historical bet slips, official actives, calibrated probabilities, or ROI invented.
"""
import argparse,hashlib,json,math,os
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from cryptography.fernet import Fernet
from scripts.phase31_accountability import verify_snapshot,canonical
from scripts.phase32_market_matching import selected_fixture,matched_forecasts
from scripts.phase28_snap_participation import name_key
from scripts.phase25_market_gate import validate_offer,joint_book_pair
from scripts.phase39_secure_quote_evidence import decrypt_archive,verify_cipher_key
from scripts.live_market import dt
from scripts.phase20_opportunity import normalize

VERSION="phase40-prospective-offer-forecast-outcome-ledger-v1"
MARKETS=("receptions","receiving_yards")

def open_archive(snapshot,cipher,key):
    verify_snapshot(snapshot)
    record=decrypt_archive(cipher,key)
    if record.get("snapshot_sha256")!=snapshot["payload_sha256"]:
        raise ValueError("Archive forecast-lock checksum mismatch")
    event=record.get("event")
    if not isinstance(event,dict):raise ValueError("Missing archived event")
    fixture=selected_fixture(snapshot,event)
    stamp=dt(record["captured_at_utc"])
    if not dt(snapshot["created_at_utc"].replace("+00:00","Z"))<stamp<dt(event["commence_time"]):
        raise ValueError("Archive captured outside frozen pregame time")
    rows=record.get("quotes")
    if not isinstance(rows,list) or len(rows)>10000:raise ValueError("Invalid archived quote list")
    for r in rows:
        if not isinstance(r,dict) or r.get("bookmaker")!="fanduel" or r.get("event_id")!=event["id"]:
            raise ValueError("Mixed event or bookmaker")
    return record,fixture

def locked_ledger(snapshot,cipher,key):
    """Point-in-time quote pairing; NO retrospective reforecast or new odds."""
    record,fixture=open_archive(snapshot,cipher,key)
    known,_=matched_forecasts(snapshot,fixture)
    # Phase32 matched_forecasts name mapping is unique within fixture; require
    # explicit unique model key for safety even if upstream behavior changes.
    forecast_names=defaultdict(list)
    for p in snapshot["forecasts"]:
        if p["fixture_id"]==fixture["id"]:
            forecast_names[name_key(p["player_name"])].append(p)
    groups=defaultdict(list);stats=Counter()
    for row in record["quotes"]:
        stats["archived_sides"]+=1
        try:validate_offer(row,record["captured_at_utc"])
        except (ValueError,TypeError,KeyError):
            stats["invalid_sides"]+=1;continue
        ident=name_key(row["player_display_name"])
        linked=forecast_names.get(ident,[])
        if len(linked)!=1:
            stats["unverified_or_ambiguous_name_sides"]+=1;continue
        if row.get("market") not in MARKETS:
            stats["unrecognized_market_sides"]+=1;continue
        p=linked[0]
        groups[(p["player_id"],row["market"],float(row["line"]))].append((p,row))
    entries=[]
    for (pid,market,line),pair in sorted(groups.items()):
        if len(pair)!=2:
            stats["unpaired_offers"]+=1;continue
        over=next(((p,r) for p,r in pair if r["side"]=="over"),None)
        under=next(((p,r) for p,r in pair if r["side"]=="under"),None)
        if not over or not under:
            stats["unpaired_offers"]+=1;continue
        try:joint_book_pair(over[1],under[1])
        except (ValueError,TypeError,KeyError):
            stats["unpaired_offers"]+=1;continue
        p=over[0]
        entries.append({"fixture_id":fixture["id"],"event_id":record["event"]["id"],
          "kickoff_utc":record["event"]["commence_time"],
          "captured_at_utc":record["captured_at_utc"],
          "snapshot_sha256":snapshot["payload_sha256"],
          "team":p["team"],"player_id":pid,"player_name":p["player_name"],
          "identity_match_method":"unique_normalized_name_not_provider_gsis_verified",
          "market":market,"frozen_projection":float(p[market]),
          "fanduel_line":line,"projection_minus_line":round(float(p[market])-line,4),
          "over_american_odds":over[1]["american_odds"],
          "under_american_odds":under[1]["american_odds"],
          "over_quote_updated_utc":over[1]["quoted_at_utc"],
          "under_quote_updated_utc":under[1]["quoted_at_utc"],
          "outcome_status":"PENDING","actual_stat":None,"over_result":None,
          "under_result":None,"absent_box_not_zero":True,
          "probability_model_validated":False,"p_over":None,"p_under":None,
          "estimated_ev":None,"bet_promoted":False,"wager_placed":False,
          "units":0})
        stats["complete_two_sided_pairs"]+=1
    ledger={"version":VERSION,"week":snapshot["week"],
      "source_archive_version":record.get("version"),
      "frozen_snapshot_sha256":snapshot["payload_sha256"],
      "archive_capture_utc":record["captured_at_utc"],
      "event":record["event"],"fixture_id":fixture["id"],
      "entries":entries,"source_quote_count":len(record["quotes"]),
      "estimated_roi":None,"official_bets":0,"units_allocated":0,
      "data_privacy":"encrypted_private_only"}
    ledger["lock_sha256"]=hashlib.sha256(canonical(ledger).encode()).hexdigest()
    return ledger,{"status":"LOCKED_PRIVATE_RESEARCH_LEDGER",
      "fixture_matched":True,"forecasts_locked_before_quotes":True,
      "counts":dict(stats),"entries_locked":len(entries),
      "provider_identity_verified":False,
      "official_actives_verified":False,"probabilities_calibrated":False,
      "official_bets":0,"units":0,"raw_quotes_exported_publicly":False}

def settle(ledger,actual,completed,asof=None):
    """Grade only if exact fixture final and source-observed individual box row.

    'completed' must derive from independently checked official/nflverse fixture
    status, not a mere caller True. Caller must supply structured proof and
    schedule final; this function does not fetch or authenticate itself.
    """
    if not isinstance(ledger,dict):raise ValueError("Invalid ledger")
    lock=ledger.get("lock_sha256")
    base={k:v for k,v in ledger.items() if k!="lock_sha256"}
    if not lock or hashlib.sha256(canonical(base).encode()).hexdigest()!=lock:
        raise ValueError("Ledger lock changed")
    if ledger.get("version")!=VERSION:raise ValueError("Unexpected ledger version")
    if not isinstance(completed,dict) or completed.get("fixture_id")!=ledger["fixture_id"] or not completed.get("final_scores_verified"):
        return None,{"status":"WAITING_FOR_VERIFIED_FINAL","graded":0}
    if asof and dt(asof)<=dt(ledger["event"]["commence_time"]):
        return None,{"status":"WAITING_FOR_KICKOFF","graded":0}
    if not isinstance(actual,dict):raise ValueError("Actuals must be identity-keyed mapping")
    graded=[];unresolved=0;counts=Counter()
    for entry in ledger["entries"]:
        key=(entry["team"],entry["player_id"])
        truth=actual.get(key)
        if truth is None:
            unresolved+=1;counts["missing_box_rows_excluded"]+=1
            continue
        if entry["market"] not in truth or truth[entry["market"]] is None:
            unresolved+=1;counts["missing_market_in_box"]+=1;continue
        val=float(truth[entry["market"]])
        if not math.isfinite(val):raise ValueError("Nonfinite actual value")
        line=entry["fanduel_line"]
        # An integer threshold is a push when actual == line.
        outcome="PUSH" if val==line else "OVER" if val>line else "UNDER"
        graded.append({**entry,"actual_stat":val,
            "outcome_status":outcome,
            "over_result":"PUSH" if outcome=="PUSH" else "WIN" if outcome=="OVER" else "LOSS",
            "under_result":"PUSH" if outcome=="PUSH" else "WIN" if outcome=="UNDER" else "LOSS",
            "absolute_projection_error":round(abs(val-entry["frozen_projection"]),4)})
        counts["graded_"+outcome.lower()]+=1
    result={"version":VERSION,"source_lock_sha256":lock,
       "final_proof":completed,"graded":graded,"unresolved":unresolved,
       "graded_count":len(graded),"official_bets":0,
       "realized_betting_profit":None,"roi":None,
       "reforecasted_after_event":False,
       "no_missing_box_converted_to_zero":True}
    return result,{"status":"SETTLED_BOX_OBSERVATIONS_ONLY",
      "graded":len(graded),"unresolved":unresolved,
      "counts":dict(counts),"placed_bets":0,"roi":None,
      "not_calibrated_probs":True}

def completed_game_from_schedule(schedule,ledger):
    """Require explicit game final scores for this event, not entire NFL week."""
    event=ledger["event"]
    from scripts.phase16 import team_id
    home=team_id(event["home_team"]);away=team_id(event["away_team"])
    if not home or not away or home==away:raise ValueError("Unknown event clubs")
    date=dt(event["commence_time"]).date()
    matches=schedule[(schedule.season==2026)&(schedule.week==ledger["week"])&
        (schedule.game_type=="REG")&(schedule.home_team==home)&
        (schedule.away_team==away)]
    matches=matches[matches.gameday.astype(str).map(
        lambda x: 0<=(date-datetime.fromisoformat(x).date()).days<=1)]
    if len(matches)!=1:raise ValueError("Schedule fixture absent or ambiguous")
    row=matches.iloc[0]
    final=bool(__import__("pandas").notna(row.home_score) and
               __import__("pandas").notna(row.away_score))
    return {"fixture_id":ledger["fixture_id"],"final_scores_verified":final,
       "schedule_source":"nflverse schedule live final scores",
       "home_score":float(row.home_score) if final else None,
       "away_score":float(row.away_score) if final else None}

def eligible_actuals(frame,ledger):
    stats=normalize(frame)
    subset=stats[(stats.season==2026)&(stats.week==ledger["week"])]
    return {(str(r.team_code),str(r.player_id)):
            {"receptions":float(r.receptions),"receiving_yards":float(r.receiving_yards)}
            for r in subset.itertuples()}

def encrypted_result(result,key):
    return Fernet(verify_cipher_key(key)).encrypt(canonical(result).encode())

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--snapshot",default="snapshots/phase31/2026-week-06.json")
    p.add_argument("--encrypted-archive",required=True)
    p.add_argument("--output-dir",default="output/phase40")
    p.add_argument("--grade-completed",action="store_true")
    a=p.parse_args()
    key=os.environ.get("QUOTE_ARCHIVE_KEY")
    verify_cipher_key(key)
    snap=json.loads(Path(a.snapshot).read_text())
    ciphertext=Path(a.encrypted_archive).read_bytes()
    ledger,manifest=locked_ledger(snap,ciphertext,key)
    out=Path(a.output_dir);out.mkdir(parents=True,exist_ok=True)
    raw=encrypted_result(ledger,key)
    (out/"locked_ledger.fernet").write_bytes(raw)
    os.chmod(out/"locked_ledger.fernet",0o600)
    manifest["encrypted_ledger_sha256"]=hashlib.sha256(raw).hexdigest()
    manifest["grade_requested"]=a.grade_completed
    if a.grade_completed:
        # Always fetch schedules from real nflverse source; only settle when
        # this PARTICULAR fixture is final. Never use 2026 future results.
        from scripts.phase18 import fetch_schedule
        from scripts.ingest import download
        folder=Path("private_data");folder.mkdir(exist_ok=True)
        schedule,source_digest=fetch_schedule(folder)
        proof=completed_game_from_schedule(schedule,ledger)
        manifest["schedule_source_sha256"]=source_digest
        if proof["final_scores_verified"]:
            frame,_=download(2026,folder)
            graded,score=settle(ledger,eligible_actuals(frame,ledger),proof,
                     datetime.now(timezone.utc).isoformat())
            if graded:
                encrypted=encrypted_result(graded,key)
                (out/"settled_ledger.fernet").write_bytes(encrypted)
                os.chmod(out/"settled_ledger.fernet",0o600)
                manifest["settled_encrypted_sha256"]=hashlib.sha256(encrypted).hexdigest()
            manifest["grade_summary"]=score
        else:
            manifest["grade_summary"]={"status":"WAITING_FOR_VERIFIED_FINAL","graded":0}
    (out/"public_aggregate.json").write_text(json.dumps(manifest,indent=2))
    summary=(f"# GRIDIRON Phase40 — Prospective FanDuel ledger\n\n"
       f"**Previously captured offer rows locked:** {manifest['entries_locked']} paired markets.\n\n"
       f"**Grade status:** {manifest.get('grade_summary',{}).get('status','NOT_REQUESTED')}.\n\n"
       "**Verified bets: 0, units: 0, ROI: N/A.**\n\n"
       "Private player lines and prices are encrypted; public report contains no player odds.\n")
    print(summary)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write(summary)
if __name__=="__main__":main()
