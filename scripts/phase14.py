"""Phase 14: private, fail-closed sportsbook-to-player pregame evidence ledger."""
import argparse,hashlib,json,math,os,re,unicodedata
from datetime import datetime,timezone
from pathlib import Path

MARKETS={"receptions","receiving_yards"}
def utc(s):
    x=datetime.fromisoformat(s.replace("Z","+00:00"))
    if x.tzinfo is None or x.utcoffset().total_seconds()!=0:raise ValueError("UTC required")
    return x
def norm(s):
    if not isinstance(s,str):return ""
    s=unicodedata.normalize("NFKD",s)
    s="".join(c for c in s if not unicodedata.combining(c))
    s=re.sub(r"[^a-z0-9 ]"," ",s.lower())
    s=re.sub(r"\b(jr|sr|ii|iii|iv)\b","",s)
    return " ".join(s.split())
def number(x):return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
def identity(q,roster):
    matches=[]
    for r in roster:
        if not isinstance(r,dict) or not r.get("player_id") or not r.get("source_ref") or not r.get("source"):continue
        if r.get("season")!=q.get("season") or r.get("team") not in (q.get("home_team"),q.get("away_team")):continue
        if norm(r.get("player_name"))!=norm(q.get("player_display_name")):continue
        try:
            if utc(r["as_of_utc"])>utc(q["captured_at_utc"]):continue
        except (KeyError,ValueError,TypeError):continue
        matches.append(r)
    unique={(x["player_id"],x["team"]) for x in matches}
    if len(unique)!=1:return ("AMBIGUOUS" if len(unique)>1 else "UNRESOLVED",None)
    return "IDENTITY_MATCHED_NOT_ACTIVE_VERIFIED",matches[0]["player_id"]
def join_quote(q,roster,projections):
    for k in ("event_id","kickoff_utc","quoted_at_utc","captured_at_utc","bookmaker","side","market"):
        if not q.get(k):raise ValueError("Missing quote "+k)
    if not isinstance(q.get("season"),int) or not 2020<=q["season"]<=2100:raise ValueError("Explicit NFL season required")
    if not utc(q["quoted_at_utc"])<=utc(q["captured_at_utc"])<utc(q["kickoff_utc"]):
        raise ValueError("Post-kickoff or future quote")
    if q["market"] not in MARKETS or q["side"] not in ("over","under"):raise ValueError("Unsupported prop")
    if not number(q.get("line")) or q["line"]<0:raise ValueError("Invalid line")
    if not isinstance(q.get("american_odds"),int) or isinstance(q["american_odds"],bool) or abs(q["american_odds"])<100:raise ValueError("Invalid price")
    status,pid=identity(q,roster)
    row={k:q.get(k) for k in ("event_id","season","player_display_name","market","side","line","american_odds","bookmaker","kickoff_utc","quoted_at_utc","captured_at_utc")}
    row.update(player_id=pid,identity_status=status,projection=None,model_probability=None,
               estimated_roi=None,decision="INSUFFICIENT_DATA",reason="player_identity_unresolved")
    if pid is None:return row
    matches=[p for p in projections if p.get("event_id")==q["event_id"] and p.get("player_id")==pid and p.get("market")==q["market"]]
    if len(matches)!=1:row["reason"]="missing_or_ambiguous_projection";return row
    p=matches[0]
    if not number(p.get("point_projection")) or p["point_projection"]<0:row["reason"]="invalid_projection";return row
    if not p.get("model_version") or not p.get("input_snapshot_sha256"):row["reason"]="unversioned_projection";return row
    try:
        if utc(p["created_at_utc"])>utc(q["quoted_at_utc"]):row["reason"]="projection_after_quote";return row
    except (KeyError,ValueError,TypeError):row["reason"]="invalid_prediction_timestamp";return row
    row.update(projection=p["point_projection"],model_version=p["model_version"],
               projection_input_hash=p["input_snapshot_sha256"],
               reason="no_book_line_calibration_or_verified_active_status")
    return row
def build_board(snapshot,roster,projections):
    if not isinstance(snapshot.get("quotes"),list):raise ValueError("Missing quotes list")
    rows=[join_quote(q,roster,projections) for q in snapshot["quotes"]]
    return {"board_type":"PRIVATE_RESEARCH_NO_BETS","schema_version":1,
            "generated_at_utc":datetime.now(timezone.utc).isoformat(),
            "rows":rows,"bets_qualified":0,"verified_roi":False,
            "calibrated_book_line_probabilities_approved":False}
def digest(board):
    return hashlib.sha256(json.dumps(board,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def settle_official_pick(pick,actual,result_source):
    if pick.get("status")!="OFFICIAL" or not pick.get("locked_at_utc"):return {"grade":"EXCLUDED_NOT_OFFICIAL"}
    if not pick.get("signed_snapshot_sha256"):return {"grade":"UNGRADED","reason":"no_immutable_snapshot"}
    try:
        if utc(pick["locked_at_utc"])>=utc(pick["kickoff_utc"]):return {"grade":"UNGRADED","reason":"late_lock"}
    except (ValueError,KeyError,TypeError):return {"grade":"UNGRADED","reason":"invalid_lock"}
    if not result_source or not result_source.get("official") or not result_source.get("source_ref"):
        return {"grade":"UNGRADED","reason":"unverified_result"}
    if not number(actual) or not number(pick.get("line")) or pick.get("market") not in MARKETS or pick.get("side") not in ("over","under"):
        return {"grade":"UNGRADED","reason":"invalid_market_or_result"}
    odds=pick.get("american_odds")
    if not isinstance(odds,int) or isinstance(odds,bool) or abs(odds)<100:return {"grade":"UNGRADED","reason":"invalid_price"}
    if actual==pick["line"]:return {"grade":"PUSH","net_units":0.}
    win=(actual>pick["line"]) if pick["side"]=="over" else (actual<pick["line"])
    return {"grade":"WIN" if win else "LOSS","net_units":round((odds/100 if odds>0 else 100/(-odds)) if win else -1.,6)}
def main():
    parser=argparse.ArgumentParser()
    for k in ("snapshot","roster","projections"):parser.add_argument("--"+k,required=True)
    parser.add_argument("--output",default="private_data/phase14_board.json")
    a=parser.parse_args()
    snapshot,roster,projections=[json.loads(Path(getattr(a,k)).read_text()) for k in ("snapshot","roster","projections")]
    if not isinstance(roster,list) or not isinstance(projections,list):raise ValueError("Roster/projections must be lists")
    board=build_board(snapshot,roster,projections);board["snapshot_sha256"]=digest(board)
    f=Path(a.output);f.parent.mkdir(parents=True,exist_ok=True)
    f.write_text(json.dumps(board,indent=2));os.chmod(f,0o600)
    print(json.dumps({"status":"PRIVATE_BOARD_PREPARED","quote_count":len(board["rows"]),
     "identity_matched":sum(x["player_id"] is not None for x in board["rows"]),
     "projections_joined":sum(x["projection"] is not None for x in board["rows"]),
     "bets_qualified":0},indent=2))
if __name__=="__main__":main()
