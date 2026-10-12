"""Local Phase 19 encrypted-ledger parsing; never logs a secret or raw quotes."""
import json,hashlib
import pandas as pd
from cryptography.fernet import Fernet,InvalidToken
MARKETS=("receptions","receiving_yards")
def decrypt_document(blob,key):
    try:
        obj=json.loads(Fernet(key.strip().encode("ascii")).decrypt(blob))
    except (ValueError,InvalidToken,UnicodeError,TypeError,json.JSONDecodeError):
        raise ValueError("Invalid archive key or encrypted file") from None
    if not isinstance(obj,dict) or obj.get("schema_version")!=1:
        raise ValueError("Unsupported Phase 19 archive")
    return obj
def document_digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def validate_pair(comparison,forecast=None):
    if not isinstance(comparison.get("matched_quotes"),list) or not isinstance(comparison.get("summary"),dict):
        raise ValueError("This is not a Phase 19 comparison archive")
    if forecast is not None:
        if not isinstance(forecast.get("predictions"),list):
            raise ValueError("Invalid frozen forecast archive")
        if document_digest(forecast)!=comparison.get("frozen_forecast_sha256"):
            raise ValueError("The two encrypted archives are not from the same run")
def normalized_quotes(comparison):
    validate_pair(comparison)
    records=[]
    for q in comparison["matched_quotes"]:
        if q.get("market") not in MARKETS or q.get("side") not in ("over","under"):continue
        try:p=float(q["locked_projection"]);line=float(q["line"]);price=int(q["american_odds"])
        except (KeyError,ValueError,TypeError):continue
        records.append({"Player":str(q.get("player_display_name") or "Unknown"),
          "Market":q["market"],"Book":str(q.get("bookmaker","")),
          "Side":q["side"],"Line":line,"Odds":price,"Projection":p,
          "Gap":round(p-line,3),"Updated after lock":bool(q.get("book_quote_updated_after_lock",False)),
          "Quoted UTC":str(q.get("quoted_at_utc","")),
          "Captured UTC":str(q.get("captured_at_utc","")),
          "Decision":"RESEARCH ONLY — NOT A BET","_player_id":str(q.get("player_id",""))})
    return pd.DataFrame(records,columns=["Player","Market","Book","Side","Line","Odds","Projection","Gap","Updated after lock","Quoted UTC","Captured UTC","Decision","_player_id"])
def player_summary(frame):
    columns=["Player","Market","Projection","Books","Distinct lines","Low line","High line","Median line","Gap to median","Quote outcomes"]
    rows=[]
    if frame.empty:return pd.DataFrame(columns=columns)
    for (pid,market),g in frame.groupby(["_player_id","Market"]):
        if g.Projection.nunique()!=1:raise ValueError("Conflicting forecast for player-market")
        lines=g.Line.drop_duplicates()
        median=float(lines.median());point=float(g.Projection.iloc[0])
        rows.append({"Player":g.Player.iloc[0],"Market":market,"Projection":point,"Books":g.Book.nunique(),
          "Distinct lines":len(lines),"Low line":lines.min(),"High line":lines.max(),
          "Median line":median,"Gap to median":round(point-median,3),"Quote outcomes":len(g)})
    return pd.DataFrame(rows,columns=columns).sort_values("Gap to median",key=lambda x:x.abs(),ascending=False)
