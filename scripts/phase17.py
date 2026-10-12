"""Phase 17: source-tracked historical-only player point projections against live lines.

No game-day actives, no guaranteed 2026 recent form, no probability/EV.
Historical (2021-2025) player-week rows are strictly earlier than 2026 games.
One-event live mode consumes API credits only with --live.
"""
import argparse,hashlib,json,os
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from scripts.ingest import URL,MEASURES,download,prior_game_features
from scripts.phase15 import acquire
from scripts.phase14 import identity,utc,norm
from scripts.phase16 import team_id
from scripts.live_market import live_check

MARKETS=("receptions","receiving_yards")
FEATURES=["prior5_"+k for k in MEASURES]+["prior3_"+k for k in MEASURES]
VERSION="phase17-ridge-historical-only-v1"
MIN_HISTORY=3

def latest_prior(frame):
    """All observed rows in historical input precede the 2026 target season."""
    required={"season","week","player_id","position",*MEASURES}
    if not required.issubset(frame.columns):raise ValueError("Missing historical fields")
    if frame.empty or (frame["season"]>=2026).any():raise ValueError("Only pre-2026 history allowed in this model")
    x=frame.sort_values(["player_id","season","week"])
    if x.duplicated(["player_id","season","week"]).any():raise ValueError("Duplicate stats player-week")
    feat=prior_game_features(x)
    # Recalculate lagged features for a *future* 2026 game, using the last
    # 3/5 observed historical games; do not use the final game's shifted values.
    records=[]
    for player,grp in x.groupby("player_id",sort=False):
        if len(grp)<MIN_HISTORY:continue
        last=grp.tail(5)
        record={"player_id":str(player),"prior_position":str(grp.iloc[-1]["position"]).upper(),
                "prior_observations":len(grp),"last_observed_season":int(grp.iloc[-1]["season"]),
                "last_observed_week":int(grp.iloc[-1]["week"])}
        for m in MEASURES:
            v=pd.to_numeric(last[m],errors="coerce")
            record["prior5_"+m]=float(v.mean()) if v.notna().any() else 0.
            v3=pd.to_numeric(last.tail(3)[m],errors="coerce")
            record["prior3_"+m]=float(v3.mean()) if v3.notna().any() else 0.
        records.append(record)
    return pd.DataFrame.from_records(records)

def fit_models(frame):
    f=prior_game_features(frame)
    f=f[(f["season"]<=2025)&(f["prior_observations"]>=MIN_HISTORY)].copy()
    models={}
    for pos in ("RB","WR","TE"):
        for market in MARKETS:
            subset=f[(f["prior_position"]==pos)&f[market].notna()&
                     f["prior5_"+market].notna()]
            if len(subset)<100:continue
            model=make_pipeline(SimpleImputer(strategy="constant",fill_value=0),
                  StandardScaler(),Ridge(alpha=10.))
            model.fit(subset[FEATURES],subset[market])
            models[(pos,market)]=model
    return models

def evaluate(quotes,roster,history,source_hashes,captured):
    if not quotes:return [],{"status":"no_upcoming_quotes","outcomes":0,"bets_qualified":0}
    if any(int(q["season"])!=2026 or utc(q["kickoff_utc"])<=utc(captured) for q in quotes):
        raise ValueError("Future 2026 kickoff required")
    prior=latest_prior(history)
    if prior.empty:raise ValueError("No historical features")
    lookup=prior.set_index("player_id",drop=False)
    models=fit_models(history)
    if not models:raise ValueError("No fitted market models")
    model_hash=hashlib.sha256(json.dumps(source_hashes,sort_keys=True).encode()).hexdigest()
    group={}
    for q in quotes:
        home=team_id(q.get("home_team"));away=team_id(q.get("away_team"))
        if not home or not away or home==away:continue
        row={**q,"home_team":home,"away_team":away}
        status,pid=identity(row,roster)
        if status!="IDENTITY_MATCHED_NOT_ACTIVE_VERIFIED" or not pid:continue
        for market in MARKETS:
            if market!=q["market"]:continue
            key=(q["event_id"],pid,market)
            if key in group:continue
            group[key]={"quote":q,"player_id":pid}
    projections=[]
    by_market=Counter();missing_history=0;stale=0
    for (event,pid,market),datum in group.items():
        if pid not in lookup.index:
            missing_history+=1;continue
        player=lookup.loc[pid]
        # No 2026 observed history available: prior season-only estimates
        # flagged as stale; useful solely as diagnostic, never betting advice.
        pos=player["prior_position"]
        model=models.get((pos,market))
        if model is None:continue
        x=pd.DataFrame([{k:player[k] for k in FEATURES}])
        point=max(0.,float(model.predict(x)[0]))
        if int(player["last_observed_season"])<2025:stale+=1
        projections.append({"event_id":event,"player_id":pid,
          "market":market,"point_projection":round(point,3),
          "created_at_utc":captured,"model_version":VERSION,
          "input_snapshot_sha256":model_hash,
          "last_historical_season":int(player["last_observed_season"]),
          "last_historical_week":int(player["last_observed_week"]),
          "eligibility_status":"NOT_ACTIVE_VERIFIED",
          "forecast_scope":"historical-only-prior-season",
          "book_line_probability":None,"bet_decision":"INSUFFICIENT_DATA"})
        by_market[market]+=1
    forecast_map={(p["event_id"],p["player_id"],p["market"]):p["point_projection"] for p in projections}
    gaps=[];covered_quotes=0
    for q in quotes:
        home=team_id(q.get("home_team"));away=team_id(q.get("away_team"))
        if not home or not away:continue
        status,pid=identity({**q,"home_team":home,"away_team":away},roster)
        if status!="IDENTITY_MATCHED_NOT_ACTIVE_VERIFIED":continue
        pred=forecast_map.get((q["event_id"],pid,q["market"]))
        if pred is None or not isinstance(q.get("line"),(float,int)):continue
        gap=pred-float(q["line"])
        gaps.append(gap);covered_quotes+=1
    spread={"compared_outcomes":covered_quotes,
       "positive_projection_line_gaps":sum(x>0 for x in gaps),
       "negative_projection_line_gaps":sum(x<0 for x in gaps),
       "equal_projection_line_gaps":sum(x==0 for x in gaps),
       "mean_absolute_projection_line_gap":round(float(np.mean(np.abs(gaps))),3) if gaps else None}
    return projections,{"status":"phase17_historical_only_live_line_comparison",
        "projection_line_diagnostics":spread,
        "captured_at_utc":captured,"unique_matched_players_market_pairs":len(group),
        "point_projections":len(projections),"projection_count_by_market":dict(by_market),
        "missing_historical_players":missing_history,
        "last_observed_before_2025":stale,
        "outcomes":len(quotes),"source_hashes":source_hashes,
        "model_version":VERSION,"2026_current_form_included":False,
        "matchup_features_included":False,"official_actives_verified":False,
        "book_line_probability_calibrated":False,
        "bets_qualified":0,"roi_verified":False,
        "player_level_rows_public":False}

def fetch_history(folder):
    frames=[];sources={}
    for year in range(2021,2026):
        frame,meta=download(year,folder)
        frames.append(frame)
        sources[str(year)]=meta["sha256"]
    return pd.concat(frames,ignore_index=True),sources

def execute(key,region,folder):
    roster,roster_audit=acquire(2026,folder)
    history,hashes=fetch_history(folder)
    # Quote request ONLY after roster, history and model inputs exist.
    quotes,quote_audit=live_check(key,region)
    captured=quote_audit.get("captured_at_utc")
    if not captured:
        captured=datetime.now(timezone.utc).isoformat()
    if quotes and utc(roster_audit["retrieved_at_utc"])>utc(captured):
        raise ValueError("Roster acquired after sportsbook quote")
    projections,report=evaluate(quotes,roster,history,hashes,captured)
    report["roster_sha256"]=roster_audit["source_sha256"]
    report["quota"]=quote_audit.get("quota",{})
    report["books"]=quote_audit.get("bookmakers",[])
    return projections,report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--live",action="store_true",help="Spend credits for ONE game after source downloads")
    p.add_argument("--region",choices=("us","us2","ca"),default="us")
    p.add_argument("--summary",default="output/phase17_summary.json")
    a=p.parse_args()
    if not a.live:p.error("Live mode is opt-in; run --help or unit tests without credits")
    folder=Path("private_data");folder.mkdir(parents=True,exist_ok=True)
    predictions,report=execute(os.getenv("ODDS_API_KEY"),a.region,folder)
    private=folder/"phase17_predictions.json"
    private.write_text(json.dumps(predictions,indent=2));os.chmod(private,0o600)
    dest=Path(a.summary);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
if __name__=="__main__":main()
