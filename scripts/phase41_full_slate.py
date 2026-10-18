"""Phase41: opt-in remaining-future NFL slate quote capture and unified encrypted ledger.

Source-of-truth is the original Phase31 freeze. Existing Phase40 ledger is
imported without altering original player projections or archived market prices.
Never publish plaintext FanDuel odds, player market combos or decryption keys.
"""
import argparse,hashlib,html,json,os
from pathlib import Path
from datetime import datetime,timezone
from cryptography.fernet import Fernet
from scripts.phase31_accountability import verify_snapshot,canonical
from scripts.phase32_market_matching import discover,selected_fixture
from scripts.phase39_secure_quote_evidence import encrypt_fanduel_event,verify_cipher_key,decrypt_archive
from scripts.phase40_prospective_ledger import locked_ledger,encrypted_result,VERSION as LEDGER_VERSION
from scripts.live_odds_smoke import fetch_json,SPORT,MARKETS
from scripts.live_market import normalize,dt

VERSION="phase41-full-slate-capture-and-unified-private-dashboard-v1"
def inspect_import(cipher,key,snapshot):
    doc=decrypt_archive(cipher,key)
    if doc.get("version")!=LEDGER_VERSION:raise ValueError("Existing ledger version mismatch")
    check=doc.get("lock_sha256")
    if not check or hashlib.sha256(canonical({k:v for k,v in doc.items() if k!="lock_sha256"}).encode()).hexdigest()!=check:
        raise ValueError("Imported ledger lock digest invalid")
    if doc.get("frozen_snapshot_sha256")!=snapshot["payload_sha256"]:
        raise ValueError("Imported ledger does not share frozen forecast snapshot")
    if doc.get("week")!=snapshot["week"]:raise ValueError("Different week in archive")
    entries=doc.get("entries")
    if not isinstance(entries,list) or len(entries)>20000:raise ValueError("Invalid archive entry list")
    for e in entries:
        if e.get("snapshot_sha256")!=snapshot["payload_sha256"]:
            raise ValueError("Mixed row snapshot hashes")
        if e.get("fixture_id") not in {f["id"] for f in snapshot["fixtures"]}:
            raise ValueError("Unknown archived fixture")
        if e.get("wager_placed") or e.get("bet_promoted"):raise ValueError("Historical bet state inconsistent")
    return doc

def combine(snapshot,prior,additions):
    verify_snapshot(snapshot)
    if prior and prior["frozen_snapshot_sha256"]!=snapshot["payload_sha256"]:
        raise ValueError("Mixed snapshot")
    records=([prior] if prior else [])+list(additions)
    rows=[];fixtures=set();seen=set();sources=[]
    for record in records:
        if not record:continue
        if record["frozen_snapshot_sha256"]!=snapshot["payload_sha256"]:
            raise ValueError("Inconsistent prior freeze")
        for e in record["entries"]:
            signature=(e["fixture_id"],e["player_id"],e["market"],float(e["fanduel_line"]))
            if signature in seen:
                raise ValueError("Duplicate player-market-line from overlapping event captures")
            seen.add(signature);rows.append(e);fixtures.add(e["fixture_id"])
        sources.append({"fixture_id":record["fixture_id"],
            "event_id":record["event"]["id"],"capture":record["archive_capture_utc"],
            "locked_pairs":len(record["entries"])})
    rows.sort(key=lambda r:(r["fixture_id"],r["player_name"],r["market"],r["fanduel_line"]))
    out={"version":LEDGER_VERSION,"phase41_version":VERSION,
      "week":snapshot["week"],"source_archive_version":"multi-event-frozen-preserved",
      "frozen_snapshot_sha256":snapshot["payload_sha256"],
      "archive_capture_utc":snapshot["created_at_utc"],
      "event":records[0]["event"] if records else None,
      "fixture_id":"MULTI_EVENT_WEEK_%02d"%snapshot["week"],
      "events":[r["event"] for r in records],"sources":sources,
      "entries":rows,"source_quote_count":sum(r["source_quote_count"] for r in records),
      "estimated_roi":None,"official_bets":0,"units_allocated":0,
      "data_privacy":"encrypted_private_only",
      "qualification":"RESEARCH_ONLY_UNVERIFIED_PLAYER_ACTIVES_AND_PROBABILITY"}
    out["lock_sha256"]=hashlib.sha256(canonical(out).encode()).hexdigest()
    return out

def live_capture(snapshot,old,key,odds_key,max_events,region,discover_fn=discover,fetch_fn=fetch_json):
    verify_snapshot(snapshot);verify_cipher_key(key)
    if not isinstance(max_events,int) or not 0<=max_events<=13:raise ValueError("Max events 0..13")
    if region not in ("us","us2","ca"):raise ValueError("Unsupported region")
    if not odds_key:raise ValueError("Explicit live mode requires ODDS_API_KEY")
    now=datetime.now(timezone.utc)
    already={old["fixture_id"]} if old else set()
    scheduled=discover_fn(odds_key,snapshot)
    eligible=[]
    for event in scheduled:
        if dt(event["commence_time"])<=now:continue
        fixture=selected_fixture(snapshot,event)
        if fixture["id"] not in already:
            eligible.append(event)
    eligible=eligible[:max_events]
    new=[];skipped=[];attempts=0
    for event in eligible:
        # Re-check kickoff immediately before the paid per-event request.
        if dt(event["commence_time"])<=datetime.now(timezone.utc):
            skipped.append("kickoff_already_started");continue
        attempts+=1
        try:
            payload,_=fetch_fn("/v4/sports/"+SPORT+"/events/"+event["id"]+"/odds",
               {"regions":region,"markets":",".join(MARKETS),
                "bookmakers":"fanduel","oddsFormat":"american"},odds_key)
            if any(payload.get(k)!=event.get(k) for k in ("id","commence_time","home_team","away_team")):
                raise ValueError("Event identity mismatch")
            if any(b.get("key")!="fanduel" for b in payload.get("bookmakers",[])):
                raise ValueError("Unexpected bookmaker")
            stamp=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
            cipher,_=encrypt_fanduel_event(snapshot,event,normalize(payload,stamp),stamp,key)
            ledger,_=locked_ledger(snapshot,cipher,key)
            new.append(ledger)
        except (ValueError,TypeError,RuntimeError,KeyError) as err:
            # No raw provider payloads/errors (sometimes include bookmaker detail)
            skipped.append("provider_or_validation_error")
            if str(err)=="API returned HTTP 429":
                break
    return new,{"events_eligible_at_discovery":len(scheduled),
        "new_requests_attempted":attempts,
        "successfully_archived_events":len(new),
        "skipped_reasons":skipped}

def offline_dashboard(snapshot,combined):
    """Static, public-safe Week 6 forecast dashboard. No real line/price data."""
    verify_snapshot(snapshot)
    rows=[]
    known={s["fixture_id"] for s in combined.get("sources",[])} if combined else set()
    for r in snapshot["forecasts"]:
        if r["fixture_id"] not in {f["id"] for f in snapshot["fixtures"]}:continue
        rows.append({"fixture":r["fixture_id"],"player":r["player_name"],
            "team":r["team"],"receptions":round(float(r["receptions"]),2),
            "yards":round(float(r["receiving_yards"]),1),
            "quote_status":"ENCRYPTED_ARCHIVE_EXISTS" if r["fixture_id"] in known else "NO_CAPTURED_MARKET"})
    fixture_ct=len({r["fixture"] for r in rows})
    safe_json=json.dumps(rows,separators=(",",":")).replace("<","\\u003c").replace(">","\\u003e").replace("&","\\u0026")
    return """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GRIDIRON Phase41 — Research Dashboard</title>
<style>body{background:#0e1118;color:#f7f8fb;font:15px system-ui;margin:0;padding:22px}header{border-bottom:2px solid #ff7714;padding-bottom:14px}h1{margin:0}small,p{color:#b1b7c5} .panel{background:#1a1f2b;border-radius:12px;padding:16px;margin:18px 0}.filters{display:flex;gap:8px;flex-wrap:wrap}select,input{padding:12px;border-radius:7px;border:1px solid #343947;background:#0f1420;color:white}input{min-width:245px}table{border-collapse:collapse;width:100%}th,td{border-bottom:1px solid #343947;padding:9px;text-align:left}th{color:#ff9b52;position:sticky;top:0;background:#171e2b}td.num{text-align:right}th.num{text-align:right}.wrap{overflow:auto;max-height:70vh} .muted{color:#939caf}a{color:#ff9b52}</style>
<header><h1>GRIDIRON <span style="color:#ff7714">WEEK 6</span></h1><p>Frozen pregame player projections · research board · prices and actual FanDuel lines are encrypted and never public</p></header>
<div class="panel"><b>READ THIS FIRST</b><p>These are forecasts, NOT approved picks, not verified +EV, and not game-day active confirmations. This public board does not expose actual FanDuel prices. For captured lines and odds, open the consolidated encrypted ledger in the local GRIDIRON private viewer.</p></div>
<div class="panel filters"><input id="search" placeholder="Search player or team"><select id="game"><option value="">All games</option></select><select id="sort"><option value="yards">Highest yards projection</option><option value="receptions">Highest receptions projection</option><option value="player">Name A–Z</option></select></div>
<div class="panel"><b id="count"></b><div class="wrap"><table><thead><tr><th>Fixture</th><th>Player</th><th>Team</th><th class="num">Receptions</th><th class="num">Receiving yards</th><th>Quote archive</th><th>Decision</th></tr></thead><tbody id="body"></tbody></table></div></div>
<script>const data=DATA_GOES_HERE;const $=id=>document.getElementById(id);for(const game of [...new Set(data.map(x=>x.fixture))].sort()){const o=document.createElement('option');o.value=game;o.textContent=game;$('game').append(o)}function render(){const q=$('search').value.toLowerCase(),g=$('game').value,sort=$('sort').value;let rows=data.filter(x=>(!g||x.fixture===g)&&(!q||[x.player,x.fixture,x.team].join(' ').toLowerCase().includes(q)));rows.sort((a,b)=>sort==='player'?a.player.localeCompare(b.player):b[sort]-a[sort]);const tbody=$('body');tbody.textContent='';for(const p of rows){const tr=document.createElement('tr');for(const v of [p.fixture,p.player,p.team,p.receptions,p.yards,p.quote_status,'RESEARCH ONLY']){const td=document.createElement('td');td.textContent=v;tr.append(td)}tbody.append(tr)}$('count').textContent=rows.length+' forecasts shown · '+new Set(rows.map(x=>x.fixture)).size+' fixtures'}for(const x of ['search','game','sort'])$(x).addEventListener('input',render);render()</script></html>""".replace("DATA_GOES_HERE",safe_json)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--snapshot",default="snapshots/phase31/2026-week-06.json")
    p.add_argument("--existing-ledger",default="")
    p.add_argument("--output-dir",default="output/phase41")
    p.add_argument("--live",action="store_true")
    p.add_argument("--max-events",type=int,default=13)
    p.add_argument("--region",choices=["us","us2","ca"],default="us")
    a=p.parse_args()
    snapshot=json.loads(Path(a.snapshot).read_text());verify_snapshot(snapshot)
    out=Path(a.output_dir);out.mkdir(parents=True,exist_ok=True)
    old=None;new=[];status={"new_requests_attempted":0,"successfully_archived_events":0}
    key=os.environ.get("QUOTE_ARCHIVE_KEY")
    if a.existing_ledger or a.live:verify_cipher_key(key)
    if a.existing_ledger:old=inspect_import(Path(a.existing_ledger).read_bytes(),key,snapshot)
    if a.live:
        new,status=live_capture(snapshot,old,key,os.environ.get("ODDS_API_KEY"),a.max_events,a.region)
    all_ledger=combine(snapshot,old,new) if old or new else None
    if all_ledger:
        encrypted=encrypted_result(all_ledger,key)
        target=out/"locked_full_slate.fernet";target.write_bytes(encrypted);os.chmod(target,0o600)
    (out/"GRIDIRON_Week6_Public_Research_Dashboard.html").write_text(offline_dashboard(snapshot,all_ledger))
    counts={"version":VERSION,"week":snapshot["week"],"frozen_snapshot_sha256":snapshot["payload_sha256"],
      "frozen_fixtures":len(snapshot["fixtures"]),"frozen_predictions":len(snapshot["forecasts"]),
      "quote_archived_fixtures":len({s["fixture_id"] for s in all_ledger["sources"]}) if all_ledger else 0,
      "paired_market_rows":len(all_ledger["entries"]) if all_ledger else 0,
      "previous_archive_preserved":bool(old),"live_collection_requested":a.live,
      "capture":status,"qualified_bets":0,"units_allocated":0,
      "fan_duel_quotes_in_public_html":False,"probabilities_calibrated":False,
      "official_player_active_verified":False}
    (out/"public_summary.json").write_text(json.dumps(counts,indent=2))
    summary=("# GRIDIRON Phase41 — Unified NFL slate\n\n"
       f"**Frozen games:** {counts['frozen_fixtures']}; **archived games:** {counts['quote_archived_fixtures']}; "
       f"**matched research market pairs:** {counts['paired_market_rows']}.\n\n"
       f"**New API event requests:** {status['new_requests_attempted']}.\n\n"
       "**Qualified bets: 0; units: 0.** Public HTML contains projection-only forecasts; private full-slate viewer file is encrypted.\n")
    print(summary)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write(summary)
if __name__=="__main__":main()
