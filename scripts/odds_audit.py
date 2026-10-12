"""GRIDIRON Phase 10: fail-closed historical player-prop quote validation.

No estimated betting edge, ROI or win-rate is emitted without real archived
quotes and a separately timestamped, pre-kickoff model-prediction snapshot.
Never substitute market-implied odds for a model probability.
"""
import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

FIELDS=("source_id","event_id","player_id","season","week","market","side","line",
        "american_odds","bookmaker","quoted_at_utc","kickoff_at_utc","provider_name")
MARKETS={"receptions","receiving_yards","rushing_yards","passing_yards",
         "rushing_attempts","passing_attempts"}
SIDES={"over","under"}

def parse_utc(value):
    if not isinstance(value,str) or not value.endswith("Z"):
        raise ValueError("timestamps must be UTC ISO8601 ending in Z")
    value=value.replace("Z","+00:00")
    dt=datetime.fromisoformat(value)
    if dt.utcoffset().total_seconds()!=0:
        raise ValueError("timestamp offset not UTC")
    return dt

def probability_break_even(odds):
    o=int(odds)
    if abs(o)<100 or o==0:
        raise ValueError("invalid American odds")
    return (-o)/((-o)+100) if o<0 else 100/(o+100)

def profit_per_dollar(odds):
    o=int(odds)
    if abs(o)<100 or o==0:
        raise ValueError("invalid American odds")
    return 100/(-o) if o<0 else o/100

def normalize_quotes(rows):
    accepted=[]
    keys=set()
    for lineno,row in enumerate(rows,start=2):
        if any(not str(row.get(k,"")).strip() for k in FIELDS):
            raise ValueError(f"row {lineno}: missing required value")
        if row["market"] not in MARKETS or row["side"] not in SIDES:
            raise ValueError(f"row {lineno}: unknown market/side")
        year,week=int(row["season"]),int(row["week"])
        if not 2020<=year<=2100 or not 1<=week<=23:
            raise ValueError(f"row {lineno}: invalid season/week")
        line=float(row["line"])
        if not math.isfinite(line) or line<0:
            raise ValueError(f"row {lineno}: invalid prop line")
        raw=str(row["american_odds"])
        if any(c in raw for c in (".","e","E")):
            raise ValueError(f"row {lineno}: odds must be integer")
        odds=int(raw)
        q=parse_utc(row["quoted_at_utc"])
        k=parse_utc(row["kickoff_at_utc"])
        if q>=k:
            raise ValueError(f"row {lineno}: quotation not strictly before kickoff")
        # Keep distinct timestamps, but disallow exact duplicates.
        key=(row["source_id"],row["event_id"],row["player_id"],
             row["market"],row["side"],line,row["bookmaker"],q)
        if key in keys:
            raise ValueError(f"row {lineno}: duplicate quote")
        keys.add(key)
        accepted.append({
            "source_id":row["source_id"],"event_id":row["event_id"],
            "player_id":row["player_id"],"season":year,"week":week,
            "market":row["market"],"side":row["side"],"line":line,
            "american_odds":odds,"bookmaker":row["bookmaker"],
            "quoted_at_utc":row["quoted_at_utc"],"kickoff_at_utc":row["kickoff_at_utc"],
            "provider_name":row["provider_name"],
            "break_even_probability":round(probability_break_even(odds),8),
            "payout_per_dollar":round(profit_per_dollar(odds),8),
        })
    return accepted

def audit(path,output):
    output=Path(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    report={
        "status":"awaiting_verified_historical_quotes",
        "created_at_utc":datetime.now(timezone.utc).isoformat(),
        "historical_quotes_validated":0,
        "calibrated_model_predictions_available":False,
        "backtested_roi_available":False,
        "bookmaker_market_availability_verified":False,
        "notes":"No synthetic lines, odds, player mappings or betting ROI.",
    }
    if path and Path(path).exists():
        source=Path(path)
        with source.open(newline="",encoding="utf-8") as handle:
            reader=csv.DictReader(handle)
            if not set(FIELDS).issubset(reader.fieldnames or []):
                raise ValueError("Quotes CSV missing required columns")
            records=normalize_quotes(reader)
        if not records:
            report["status"]="awaiting_verified_historical_quotes"
        else:
            report.update(status="historical_quote_schema_validated",
                          historical_quotes_validated=len(records),
                          input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                          providers=sorted(set(r["provider_name"] for r in records)),
                          bookmakers=sorted(set(r["bookmaker"] for r in records)),
                          seasons=sorted(set(r["season"] for r in records)),
                          markets=sorted(set(r["market"] for r in records)))
            # Do not publish potentially licensed quote rows to public GitHub pages.
    output.write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    return report

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--quotes",default="private_data/historical_prop_quotes.csv")
    ap.add_argument("--output",default="output/odds_audit.json")
    args=ap.parse_args()
    audit(args.quotes,args.output)
