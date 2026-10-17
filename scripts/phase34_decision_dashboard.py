"""Phase34: public, auditable pregame research dashboard, NEVER a bet card.

Displays immutable Phase31 forecasts with explicit participation, calibration
and market-evidence gates. Public outputs contain no licensed sportsbook offers.
"""
import argparse,html,json,os
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from scripts.phase31_accountability import verify_snapshot
from scripts.phase33_probability_evidence import official_availability_gate

VERSION="phase34-frozen-matchup-decision-board-v1"
SKILL_POSITIONS={"WR","RB","TE","FB"}
MARKETS=("receptions","receiving_yards")
BLOCKERS=("real_line_probability_not_validated","official_active_not_verified",
          "route_role_not_verified","individual_book_offer_not_archived",
          "opponent_and_weather_not_verified")

def player_status(forecast,position=None,evidence=None):
    """Fail closed; never upgrade from unverified booleans or supplied notes."""
    status=official_availability_gate(evidence)
    if position is not None and position not in SKILL_POSITIONS:
        return "FILTERED_NOT_SKILL_PLAYER",["non_skill_position"]
    return "RESEARCH_ONLY",list(BLOCKERS)+status["reasons"][:1]

def position_lookup(history,week):
    """Position is last-known prior season/week production metadata, not active."""
    if history is None:return {}
    from scripts.phase20_opportunity import normalize
    x=normalize(history)
    x=x[(x.season<2026)|((x.season==2026)&(x.week<week))]
    latest=x.sort_values(["season","week"]).drop_duplicates(["team_code","player_id"],keep="last")
    return {(str(r.team_code),str(r.player_id)):str(r.position).upper()
            for r in latest.itertuples()}

def build(snapshot,position_map=None,calibration=None,market_aggregate=None):
    verify_snapshot(snapshot)
    position_map=position_map or {}
    # An aggregate count of odds matches is NOT player-level evidence and
    # cannot be applied to any individual forecast.
    research_gate=bool(calibration and calibration.get("research_sample_sufficiency_gate"))
    games=[]
    counts=Counter()
    for fixture in snapshot["fixtures"]:
        players=[]
        for r in snapshot["forecasts"]:
            if r["fixture_id"]!=fixture["id"]:continue
            pos=position_map.get((r["team"],r["player_id"]))
            state,reasons=player_status(r,pos)
            counts[state]+=1
            if state=="FILTERED_NOT_SKILL_PLAYER":continue
            players.append({"player":r["player_name"],"team":r["team"],
                "player_id":r["player_id"],"position":pos or "UNVERIFIED",
                "targets":float(r["targets"]),
                "receptions":float(r["receptions"]),
                "receiving_yards":float(r["receiving_yards"]),
                "evidence_status":state,"blockers":reasons,
                "game_day_active_confirmed":False,
                "bookmaker_line_specific_probability":None,
                "expected_roi":None,
                "qualified_play":False})
        players.sort(key=lambda p:(-p["receiving_yards"],p["player"]))
        games.append({"fixture_id":fixture["id"],"away":fixture["away"],
                      "home":fixture["home"],"gameday":fixture["gameday"],
                      "players":players,"qualified_plays":0})
    return {"version":VERSION,"season":snapshot["season"],"week":snapshot["week"],
        "forecast_lock_utc":snapshot["created_at_utc"],
        "forecast_lock_sha256":snapshot["payload_sha256"],
        "champion":snapshot["model"],
        "games":games,"total_forecasts":len(snapshot["forecasts"]),
        "displayed_players":sum(len(g["players"]) for g in games),
        "filtered_non_skill_rows":counts["FILTERED_NOT_SKILL_PLAYER"],
        "players_without_position_confirmation":sum(
            p["position"]=="UNVERIFIED" for g in games for p in g["players"]),
        "calibration_historical_sufficiency_passed":research_gate,
        "calibration_real_book_lines_validated":False,
        "market_integration_historical_aggregate_available":bool(market_aggregate),
        "individual_current_book_lines_available":False,
        "official_actives_source_integrated":False,
        "game_day_weather_verified":False,
        "opponent_coverage_verified":False,
        "historical_route_data_verified":False,
        "research_candidates":sum(len(g["players"]) for g in games),
        "qualified_bets":0,"probabilities_are_not_sportsbook_calibrated":True,
        "status":"RESEARCH_ONLY_NO_QUALIFIED_BETS"}

def markdown(board):
    lines=["# GRIDIRON Phase 34 — Pregame decision dashboard","",
       f"**2026 Week {board['week']} — {len(board['games'])} frozen matchups**",
       f"Forecast lock: \`{board['forecast_lock_utc']}\`",
       f"Champion: {board['champion']}",
       f"**Research players: {board['displayed_players']} | Qualified bets: 0**","",
       "No player can be promoted until a real sportsbook-line probability and",
       "an official player-availability verification are available.","",
       "## Game-by-game frozen projections",""]
    for g in board["games"]:
        lines += [f"### {g['away']} @ {g['home']} · {g['gameday']}","",
          "| Player | Team | Pos | Targets | Rec | Rec yards | Status |",
          "|:--|:--|:--|--:|--:|--:|:--|"]
        for p in g["players"][:18]:
            lines.append(f"| {p['player'].replace('|','/')} | {p['team']} | {p['position']} | "
             f"{p['targets']:.1f} | {p['receptions']:.1f} | {p['receiving_yards']:.1f} | Research only |")
        lines.append("")
    lines+=["## Evidence gates","",
      "| Required evidence | Status |","|:--|:--|",
      "| Historical research calibration | "+("Preliminary sufficiency" if board["calibration_historical_sufficiency_passed"] else "Insufficient")+" |",
      "| Real bookmaker line-specific probability | Missing |",
      "| Official game-day player active status | Missing |",
      "| Verified player route role | Missing |",
      "| Opponent coverage and weather | Missing |",
      "| Qualified bets | **0** |",
      "","**These are frozen projections, not player prop selections or priced betting opportunities.**"]
    return "\n".join(lines)+"\n"

def webpage(board):
    """Fully standalone static HTML, escaped fields and no remote scripts."""
    esc=lambda x:html.escape(str(x),quote=True)
    nav="".join(f'<a href="#{esc(g["fixture_id"])}">{esc(g["away"])} @ {esc(g["home"])}</a>'
       for g in board["games"])
    sections=[]
    for g in board["games"]:
        trs=[]
        for p in g["players"]:
            trs.append("<tr>"+''.join(f"<td>{esc(v)}</td>" for v in (
                p["player"],p["team"],p["position"],f'{p["targets"]:.1f}',
                f'{p["receptions"]:.1f}',f'{p["receiving_yards"]:.1f}',
                "RESEARCH ONLY"))+"</tr>")
        sections.append(f'<section id="{esc(g["fixture_id"])}"><h2>{esc(g["away"])} @ {esc(g["home"])}</h2>'
          f'<p class="sub">{esc(g["gameday"])} · Frozen Phase 23 role model</p>'
          '<div class="overflow"><table><thead><tr><th>Player</th><th>Team</th><th>Pos</th>'
          '<th>Targets</th><th>Receptions</th><th>Rec yards</th><th>Evidence</th></tr></thead>'
          "<tbody>"+"".join(trs)+"</tbody></table></div></section>")
    css="""body{margin:0;background:#090e16;color:#e9eef6;font:15px system-ui,sans-serif}
    header{padding:32px max(24px,calc((100vw - 1200px)/2));border-bottom:1px solid #243043}
    h1{font-size:28px;margin:0 0 8px}h2{font-size:21px;margin:0 0 6px}
    main{max-width:1200px;margin:auto;padding:20px 24px 70px}.sub,small{color:#9fabc0}
    .stats{display:flex;gap:12px;flex-wrap:wrap;margin-top:20px}.stat{background:#152033;padding:16px;border-radius:12px;min-width:140px}
    .num{font-size:26px;font-weight:750;display:block}nav{display:flex;gap:8px;overflow:auto;padding:20px 0;white-space:nowrap}
    nav a{background:#172334;color:#dce8f8;padding:9px 12px;border-radius:20px;text-decoration:none}
    section{background:#101a28;border:1px solid #26354a;padding:20px;margin:18px 0;border-radius:13px}
    .overflow{overflow:auto}table{border-collapse:collapse;width:100%;white-space:nowrap;margin-top:18px}
    th{text-align:left;font-size:12px;color:#a3b3c8}td,th{padding:10px 12px;border-bottom:1px solid #273349}
    td:nth-child(n+4):nth-child(-n+6){font-variant-numeric:tabular-nums}
    .notice{border-left:3px solid #ff8a34;background:#211a19;padding:14px 18px;margin:18px 0;border-radius:5px}
    .foot{color:#9fabc0;margin-top:24px}"""
    return ('<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>GRIDIRON — Week {board["week"]} Research</title>'
        f'<style>{css}</style>'
        '<header><h1>GRIDIRON <span style="color:#ff8a34">/ Research Board</span></h1>'
        f'<div class="sub">2026 Week {board["week"]} · Frozen {esc(board["forecast_lock_utc"])}</div>'
        '<div class="stats">'
        f'<div class="stat"><span class="num">{len(board["games"])}</span>Games</div>'
        f'<div class="stat"><span class="num">{board["displayed_players"]}</span>Player forecasts</div>'
        '<div class="stat"><span class="num">0</span>Qualified bets</div></div></header>'
        '<main><div class="notice"><strong>Research only.</strong> '
        'Official actives, real-line calibrated probabilities, verified receiving routes and current individual odds are unavailable. '
        'Do not treat point projections as +EV bets.</div>'
        f'<nav aria-label="Matchups">{nav}</nav>'
        + "".join(sections)
        + '<p class="foot">No bookmaker prices, wagering claims or API keys are included. '
        'Generated entirely from immutable pregame GRIDIRON forecasts.</p></main></html>')

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--snapshot",default="snapshots/phase31/2026-week-06.json")
    p.add_argument("--output-dir",default="output/phase34")
    p.add_argument("--use-player-position-history",action="store_true")
    a=p.parse_args()
    snap=json.loads(Path(a.snapshot).read_text())
    positions={}
    if a.use_player_position_history:
        import pandas as pd
        from scripts.ingest import download
        folder=Path("private_data");folder.mkdir(exist_ok=True)
        pieces=[download(y,folder)[0] for y in (2025,2026)]
        positions=position_lookup(pd.concat(pieces,ignore_index=True),snap["week"])
    board=build(snap,positions)
    out=Path(a.output_dir);out.mkdir(parents=True,exist_ok=True)
    (out/"decision_dashboard.json").write_text(json.dumps(board,indent=2))
    (out/"decision_dashboard.md").write_text(markdown(board))
    (out/"decision_dashboard.html").write_text(webpage(board))
    message=(f"# GRIDIRON Phase 34 — Decision board\n\n"
       f"Frozen Week {board['week']}: **{len(board['games'])} games**, "
       f"**{board['displayed_players']} displayed player forecasts**, "
       f"**{board['filtered_non_skill_rows']} non-skill filtered**, "
       f"**0 qualified bets**.\n\n"
       "The HTML dashboard is in the uploaded GitHub Actions artifact. "
       "No sportsbook credits used.\n")
    print(message)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as file:file.write(message)
if __name__=="__main__":main()
