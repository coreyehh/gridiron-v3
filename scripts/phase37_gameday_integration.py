"""Phase 37: integrated, executable FanDuel game-day decision evidence flow.

Public report = pregame frozen forecasts + evidence status, not licensed odds.
Opt-in live mode checks ONE upcoming FanDuel game and matches two-sided quotes
against those frozen forecasts in memory. It never claims official NFL actives,
calibrated P(win), model EV or accepted FanDuel parlay prices.
"""
import argparse,hashlib,html,json,os
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from scripts.phase31_accountability import verify_snapshot,canonical
from scripts.phase32_market_matching import selected_fixture,matched_forecasts,discover
from scripts.phase25_market_gate import validate_offer,joint_book_pair
from scripts.phase28_snap_participation import name_key
from scripts.phase34_decision_dashboard import build as frozen_board,position_lookup,webpage
from scripts.phase35_fanduel_portfolio import bankroll_config,BOOK
from scripts.live_market import normalize,dt
from scripts.live_odds_smoke import SPORT,MARKETS,fetch_json

VERSION="phase37-integrated-fanduel-evidence-dashboard-v1"
BLOCKERS=("not_authoritative_official_active","not_verified_role_routes",
          "not_prospectively_calibrated_at_fanduel_line",
          "no_authenticated_individual_sportsbook_offer_archive",
          "opponent_context_not_verified")
PARTICIPATION={"source":"not_connected","official_active_verified":False,
               "last_verified_update_utc":None}
MINIMUM_PLAYER_GAMES_FOR_PROBABILITY=1500

def row_status(forecast,position=None):
    if position and position not in ("WR","RB","TE","FB"):
        return "EXCLUDED_NON_SKILL",["historical_position_not_skill"]
    return "RESEARCH_ONLY",list(BLOCKERS)+(["historical_position_unknown"] if not position else [])

def offline_decisions(snapshot,positions=None,bankroll=1000,unit_pct=1):
    verify_snapshot(snapshot)
    positions=positions or {}
    stake=bankroll_config(bankroll,unit_pct)
    counts=Counter()
    games=[]
    for f in snapshot["fixtures"]:
        players=[]
        for p in snapshot["forecasts"]:
            if p["fixture_id"]!=f["id"]:continue
            position=positions.get((p["team"],p["player_id"]))
            status,reasons=row_status(p,position)
            counts[status]+=1
            if status=="EXCLUDED_NON_SKILL":continue
            players.append({"player_name":p["player_name"],"player_id":p["player_id"],
              "team":p["team"],"position":position or "UNVERIFIED",
              "projected_targets":round(float(p["targets"]),2),
              "projected_receptions":round(float(p["receptions"]),2),
              "projected_receiving_yards":round(float(p["receiving_yards"]),2),
              "decision":status,"blocking_reasons":reasons,
              "fanduel_individual_offer_verified":False,
              "official_active_verified":False,"p_win_at_actual_fanduel_line":None,
              "expected_roi":None,"units":0,"qualified":False})
        players.sort(key=lambda p:(-p["projected_receiving_yards"],p["player_name"]))
        games.append({"fixture_id":f["id"],"matchup":f["away"]+" @ "+f["home"],
            "gameday":f["gameday"],"research_players":players})
    return {"version":VERSION,"season":snapshot["season"],"week":snapshot["week"],
      "model":snapshot["model"],"forecast_snapshot_sha256":snapshot["payload_sha256"],
      "forecast_locked_utc":snapshot["created_at_utc"],
      "fixtures":games,"forecasts_total":len(snapshot["forecasts"]),
      "player_rows":sum(len(x["research_players"]) for x in games),
      "non_skill_excluded":counts["EXCLUDED_NON_SKILL"],
      "bankroll_policy":stake,"availability_source":PARTICIPATION,
      "market_audit":{"status":"not_requested"},
      "independently_validated_probability_player_games":0,
      "independently_validated_real_fanduel_line_probabilities":False,
      "fanduel_2_to_5_leg_combined_quote_validated":False,
      "qualified_singles":[],"qualified_parlays":{str(i):[] for i in range(2,6)},
      "allocated_units":0,"staked_dollars":0,
      "no_wagers_placed":True,
      "decision":"RESEARCH_ONLY_WAIT_FOR_EVIDENCE"}

def match_live_fanduel(snapshot,payload,captured_at_utc):
    """Actual quote-side match *in memory*, public aggregate only."""
    event={k:payload.get(k) for k in ("id","home_team","away_team","commence_time")}
    fixture=selected_fixture(snapshot,event)
    now=dt(captured_at_utc)
    if not dt(snapshot["created_at_utc"].replace("+00:00","Z"))<now<dt(event["commence_time"]):
        raise ValueError("Quote capture not between forecast freeze and kickoff")
    books=payload.get("bookmakers")
    if not isinstance(books,list) or any(b.get("key")!="fanduel" for b in books):
        raise ValueError("Expected FanDuel only")
    quotes=normalize(payload,captured_at_utc)
    predictions,_=matched_forecasts(snapshot,fixture)
    pairs=defaultdict(list);counts=Counter()
    for q in quotes:
        counts["quote_sides_seen"]+=1
        if q.get("bookmaker")!="fanduel":raise ValueError("Other sportsbook quote")
        try:validate_offer(q,captured_at_utc)
        except (ValueError,TypeError,KeyError):
            counts["stale_invalid_sides"]+=1;continue
        p=predictions.get(name_key(q["player_display_name"]))
        if p is None:
            counts["unmatched_player_sides"]+=1;continue
        counts["matched_player_sides"]+=1
        k=(q["event_id"],name_key(q["player_display_name"]),q["market"],q["line"])
        pairs[k].append(q)
    unique=set()
    for key,group in pairs.items():
        if len(group)!=2:
            counts["unpaired_market_groups"]+=1;continue
        over=next((q for q in group if q["side"]=="over"),None)
        under=next((q for q in group if q["side"]=="under"),None)
        if over is None or under is None:
            counts["unpaired_market_groups"]+=1;continue
        try:joint_book_pair(over,under)
        except (ValueError,TypeError,KeyError):
            counts["unpaired_market_groups"]+=1;continue
        counts["valid_fanduel_two_sided_pairs"]+=1
        counts["valid_"+over["market"]+"_pairs"]+=1
        unique.add(key[1])
    counts["unique_name_matched_players_with_pairs"]=len(unique)
    return {"status":"live_fanduel_one_fixture_matched",
       "frozen_fixture":fixture["id"],"counts":dict(sorted(counts.items())),
       "provider_id_player_verified":False,
       "official_active_status_verified":False,
       "point_in_time_probability_calibration_verified":False,
       "raw_quote_rows_exported":False,
       "parlay_price_verified":False,
       "qualified_singles":0,"qualified_parlays":0}

def live_once(snapshot,key,region="us",event_id=""):
    if not key:raise ValueError("Missing ODDS_API_KEY")
    if region not in ("us","us2","ca"):raise ValueError("Unknown region")
    try:events=discover(key,snapshot,event_id)
    except RuntimeError as e:
        if str(e)=="API returned HTTP 429":
            return {"status":"provider_http_429_no_retry","paid_event_quote_request_made":False}
        raise
    if not events:return {"status":"no_upcoming_frozen_fixture","paid_event_quote_request_made":False}
    event=events[0]
    data,quota=fetch_json("/v4/sports/"+SPORT+"/events/"+event["id"]+"/odds",
       {"regions":region,"bookmakers":BOOK,"oddsFormat":"american",
        "markets":",".join(MARKETS)},key)
    if data.get("id")!=event["id"] or data.get("commence_time")!=event["commence_time"]:
        raise ValueError("Provider event/kickoff changed")
    if data.get("home_team")!=event["home_team"] or data.get("away_team")!=event["away_team"]:
        raise ValueError("Provider teams changed")
    audit=match_live_fanduel(snapshot,data,datetime.now(timezone.utc).isoformat().replace("+00:00","Z"))
    audit["paid_event_quote_request_made"]=True
    audit["quota_remaining"]=quota.get("x-requests-remaining")
    return audit

def safe_html(board):
    esc=lambda s:html.escape(str(s),quote=True)
    links="".join(f'<a href="#{esc(g["fixture_id"])}">{esc(g["matchup"])}</a>' for g in board["fixtures"])
    sections=[]
    for g in board["fixtures"]:
        trs=[]
        for p in g["research_players"]:
            cols=(p["player_name"],p["team"],p["position"],f'{p["projected_targets"]:.2f}',
                  f'{p["projected_receptions"]:.2f}',f'{p["projected_receiving_yards"]:.1f}',
                  "PASS — evidence unverified","0u")
            trs.append("<tr>"+"".join(f"<td>{esc(v)}</td>" for v in cols)+"</tr>")
        sections.append(f'<section id="{esc(g["fixture_id"])}"><h2>{esc(g["matchup"])}</h2>'
          '<table><thead><tr><th>Player</th><th>Team</th><th>Position</th><th>Targets</th>'
          '<th>Rec</th><th>Rec yards</th><th>Decision</th><th>Units</th></tr></thead><tbody>'
          + "".join(trs)+"</tbody></table></section>")
    audit=board["market_audit"]
    counts=audit.get("counts",{})
    css="""body{background:#090d15;color:#edf2fa;font:15px system-ui,sans-serif;margin:0}
    header,main{max-width:1240px;margin:auto;padding:28px 22px}h1{font-size:28px}h2{font-size:20px}
    .flag{background:#2a1a14;border-left:4px solid #ff8d38;padding:14px 18px;border-radius:6px}
    .stats{display:flex;flex-wrap:wrap;gap:12px;margin:22px 0}.stat{background:#172235;padding:16px;border-radius:12px;min-width:140px}
    .stat strong{display:block;font-size:26px}nav{display:flex;gap:8px;overflow:auto;white-space:nowrap;padding:18px 0}
    nav a{color:#e5eefb;background:#1c2a3c;padding:8px 12px;border-radius:25px;text-decoration:none}
    section{background:#101927;border:1px solid #29354a;border-radius:12px;margin:20px 0;padding:18px;overflow:auto}
    table{width:100%;border-collapse:collapse;white-space:nowrap}th,td{padding:10px;border-bottom:1px solid #2a364a;text-align:left}
    th{font-size:12px;color:#a5b6c9}small{color:#a5b6c9}"""
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
      '<title>GRIDIRON Phase37 evidence board</title><style>'+css+'</style><header>'
      '<h1>GRIDIRON <span style="color:#ff8d38">/ FanDuel Evidence Board</span></h1>'
      f'<small>Week {board["week"]} · frozen pregame predictions · FanDuel quote status: {esc(audit["status"])}</small>'
      '<div class="stats">'
      f'<div class="stat"><strong>{len(board["fixtures"])}</strong>Matchups</div>'
      f'<div class="stat"><strong>{board["player_rows"]}</strong>Research players</div>'
      f'<div class="stat"><strong>{counts.get("valid_fanduel_two_sided_pairs",0)}</strong>Private FanDuel pairs audited</div>'
      '<div class="stat"><strong>0u</strong>Wagers qualified</div></div></header><main>'
      '<div class="flag"><b>PASS: no official bets.</b> Authentic NFL game-day active records, route-role checks, '
      'real-line calibrated probabilities and FanDuel accepted parlay combined payouts remain missing. '
      'Sportsbook price comparisons are never published on this public dashboard.</div>'
      f'<nav aria-label="Matchups">{links}</nav>'+ "".join(sections)
      +'<p><small>Projection is not a betting line; model ≠ verified ROI. No keys or individual licensed quotes stored.</small></p></main></html>')

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--snapshot",default="snapshots/phase31/2026-week-06.json")
    p.add_argument("--output-dir",default="output/phase37")
    p.add_argument("--bankroll",type=float,default=1000.)
    p.add_argument("--unit-percent",type=float,default=1.)
    p.add_argument("--use-positions",action="store_true")
    p.add_argument("--live-fanduel",action="store_true")
    p.add_argument("--region",choices=["us","us2","ca"],default="us")
    p.add_argument("--event-id",default="")
    a=p.parse_args()
    snapshot=json.loads(Path(a.snapshot).read_text())
    positions={}
    if a.use_positions:
        import pandas as pd
        from scripts.ingest import download
        folder=Path("private_data");folder.mkdir(exist_ok=True)
        data=pd.concat([download(y,folder)[0] for y in (2025,2026)],ignore_index=True)
        positions=position_lookup(data,snapshot["week"])
    board=offline_decisions(snapshot,positions,a.bankroll,a.unit_percent)
    if a.live_fanduel:
        board["market_audit"]=live_once(snapshot,os.environ.get("ODDS_API_KEY"),a.region,a.event_id)
    out=Path(a.output_dir);out.mkdir(parents=True,exist_ok=True)
    (out/"fanduel_evidence_board.json").write_text(json.dumps(board,indent=2))
    (out/"fanduel_evidence_board.html").write_text(safe_html(board))
    # Immutable in-value snapshot audit checksum; no placed wagers.
    audit={"version":VERSION,"forecast_sha256":snapshot["payload_sha256"],
        "market_coverage":board["market_audit"],"unit_policy":board["bankroll_policy"],
        "qualified_singles":0,"qualified_parlays":0,"placed_wagers":0}
    audit["report_sha256"]=hashlib.sha256(canonical(audit).encode()).hexdigest()
    (out/"decision_audit.json").write_text(json.dumps(audit,indent=2))
    report=("# GRIDIRON Phase37 — Game-day evidence integration\n\n"
      f"Frozen Week {board['week']}: **{len(board['fixtures'])} games** and **{board['player_rows']} research players**.\n\n"
      f"**FanDuel market:** {board['market_audit']['status']}\n\n"
      f"**Validated paired FanDuel props:** {board['market_audit'].get('counts',{}).get('valid_fanduel_two_sided_pairs',0)}.\n\n"
      "**Official player actives authenticated:** 0. **Calibrated at live FanDuel lines:** No.\n\n"
      "**Singles: 0 | Parlays (2–5): 0 | Units allocated: 0.**\n\n"
      "Download the artifact for a standalone HTML matchup board and evidence audit. "
      "No player-level licensed offers or betting prices are published.\n")
    print(report)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write(report)
if __name__=="__main__":main()
