"""GRIDIRON Phase 8: play-by-play team passing volume + RB opportunity features.

All model inputs are strictly prior-game rolling signals. This is NOT routes,
coverage, sportsbook odds, or a verified historical pregame market universe.
"""
import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

BASE = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{}.parquet"
TEAM_COLS = ["season", "week", "posteam", "pass_attempt", "season_type"]
OLD_COLS = ["prior5_receptions","prior5_receiving_yards","prior5_rushing_yards","prior5_passing_yards",
            "prior3_receptions","prior3_receiving_yards","prior3_rushing_yards","prior3_passing_yards"]
EXTRA_COLS = ["prior_team_pass_attempts_5","prior_rb_targets_5","prior_rb_target_share_5",
              "prior_rb_catch_rate_5","prior_rb_yards_per_target_5"]
TARGETS = [("receptions", 0.75), ("receiving_yards", 7.5)]

def lag(s, window=5):
    return s.shift(1).rolling(window, min_periods=1).mean()

def download_pbp(season, output):
    path = output / ("play_by_play_%d.parquet" % season)
    url = BASE.format(season)
    with urlopen(Request(url,headers={"User-Agent":"GRIDIRON-v3/1.0"}),timeout=180) as req:
        with path.open("wb") as dst:
            shutil.copyfileobj(req,dst)
    df = pd.read_parquet(path,columns=TEAM_COLS)
    if df.empty or set(df.season.dropna().astype(int)) != {season}:
        raise ValueError("Unexpected PBP season %s" % season)
    if not df.week.between(1,23).all():
        raise ValueError("Invalid week in %s" % season)
    return df, {"season":season,"rows":int(len(df)),
                "sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"source":url}

def team_volume(pbp):
    needed={"season","week","posteam","pass_attempt","season_type"}
    if not needed.issubset(pbp.columns):
        raise ValueError("PBP missing "+str(sorted(needed-set(pbp.columns))))
    x=pbp[pbp.season_type.eq("REG") & pbp.posteam.notna()].copy()
    x["pass_attempt"]=pd.to_numeric(x.pass_attempt,errors="coerce").fillna(0)
    out=x.groupby(["season","week","posteam"],as_index=False)["pass_attempt"].sum()
    out=out.rename(columns={"posteam":"team","pass_attempt":"team_pass_attempts"})
    if out.duplicated(["season","week","team"]).any():
        raise AssertionError("Duplicate team-week")
    out=out.sort_values(["team","season","week"])
    out["prior_team_pass_attempts_5"]=out.groupby("team",sort=False)["team_pass_attempts"].transform(lag)
    return out

def build_opportunities(weekly, base_features, volume):
    required={"season","week","player_id","position","recent_team","targets","receptions","receiving_yards","season_type"}
    if not required.issubset(weekly.columns):
        raise ValueError("Player stats missing "+str(sorted(required-set(weekly.columns))))
    keys=["season","week","player_id"]
    weekly=weekly[weekly.season_type.eq("REG")].copy()
    if weekly.duplicated(keys).any():
        raise ValueError("Duplicate player-weeks in regular season")
    weekly["targets"]=pd.to_numeric(weekly.targets,errors="coerce")
    weekly["receptions"]=pd.to_numeric(weekly.receptions,errors="coerce")
    weekly["receiving_yards"]=pd.to_numeric(weekly.receiving_yards,errors="coerce")
    joined=weekly.merge(volume[["season","week","team","team_pass_attempts",
                                "prior_team_pass_attempts_5"]],
                        left_on=["season","week","recent_team"],
                        right_on=["season","week","team"],how="left",validate="many_to_one")
    joined=joined.sort_values(["player_id","season","week"])
    # share and efficiency calculated in historical week, then shifted before prediction.
    joined["week_target_share"]=np.where(joined.team_pass_attempts>0,
                                         joined.targets/joined.team_pass_attempts,np.nan)
    joined["week_catch_rate"]=np.where(joined.targets>0, joined.receptions/joined.targets,np.nan)
    joined["week_ypt"]=np.where(joined.targets>0, joined.receiving_yards/joined.targets,np.nan)
    grouping=joined.groupby("player_id",sort=False)
    for out,field in [("prior_rb_targets_5","targets"),
                      ("prior_rb_target_share_5","week_target_share"),
                      ("prior_rb_catch_rate_5","week_catch_rate"),
                      ("prior_rb_yards_per_target_5","week_ypt")]:
        joined[out]=grouping[field].transform(lag)
    features=joined[keys+EXTRA_COLS]
    out=base_features.merge(features,on=keys,how="left",validate="one_to_one",indicator=True)
    if not (out["_merge"]=="both").any():
        raise ValueError("No player-week keys joined")
    out=out.drop(columns="_merge")
    return out, {
        "pbp_team_weeks":int(len(volume)),
        "matched_player_weeks":int(out.prior_team_pass_attempts_5.notna().sum()),
        "total_player_weeks":int(len(out)),
        "rb_lagged_target_share_observations":int(((out.prior_position=="RB") &
                                          out.prior_rb_target_share_5.notna()).sum())
    }

def evaluate(frame):
    results=[]
    for market,threshold in TARGETS:
        pool=frame[(frame.prior_position=="RB") & (frame.prior_observations>=3) &
                   (frame["prior5_"+market]>=threshold) & frame[market].notna() &
                   frame.prior_team_pass_attempts_5.notna()].copy()
        a=pool[pool.season.between(2021,2023)]
        b=pool[pool.season.eq(2024)]
        c=pool[pool.season.eq(2025)]
        row={"market":market,"train_n":len(a),"validation_n":len(b),"test_n":len(c),
             "selection":"RB prior-position and lagged usage, postgame-observed player-week caveat"}
        if min(len(a),len(b),len(c))<50:
            results.append(dict(row,status="insufficient_samples"))
            continue
        scores={}
        for name,cols in [("statistical_baseline",OLD_COLS),
                          ("opportunity_model",OLD_COLS+EXTRA_COLS)]:
            best=None
            for alpha in (1.0,10.0,100.0):
                model=make_pipeline(SimpleImputer(strategy="constant",fill_value=0),
                                    StandardScaler(),Ridge(alpha=alpha))
                model.fit(a[cols],a[market])
                score=mean_absolute_error(b[market],np.maximum(0,model.predict(b[cols])))
                if best is None or score<best[0]:
                    best=(score,alpha)
            model=make_pipeline(SimpleImputer(strategy="constant",fill_value=0),
                                StandardScaler(),Ridge(alpha=best[1]))
            training=pd.concat([a,b])
            model.fit(training[cols],training[market])
            preds=np.maximum(0,model.predict(c[cols]))
            scores[name]={"mae":float(mean_absolute_error(c[market],preds)),
                          "rmse":float(np.sqrt(mean_squared_error(c[market],preds))),
                          "alpha":best[1]}
        old=scores["statistical_baseline"]["mae"];new=scores["opportunity_model"]["mae"]
        results.append(dict(row,status="evaluated",baseline=scores["statistical_baseline"],
                            opportunity=scores["opportunity_model"],
                            opportunity_mae_change_pct=round(100*(old-new)/old,2),
                            improves_on_same_population=bool(new<old)))
    return {"status":"rb_opportunity_holdout_2025","train_years":[2021,2022,2023],
            "validation_year":2024,"heldout_year":2025,
            "evaluated_at_utc":datetime.now(timezone.utc).isoformat(),
            "sources":["nflverse player-week stats","nflverse play-by-play"],
            "routes_available":False,"coverage_available":False,
            "pregame_active_universe_complete":False,
            "historic_sportsbook_odds_available":False,"roi_calculated":False,
            "results":results}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",default="output")
    p.add_argument("--seasons",type=int,nargs="+",default=[2021,2022,2023,2024,2025])
    args=p.parse_args()
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    pbps=[];provenance=[];weeks=[]
    for year in args.seasons:
        df,meta=download_pbp(year,out)
        pbps.append(df);provenance.append(meta)
        stats=pd.read_parquet(out/("stats_player_week_%d.parquet"%year))
        weeks.append(stats)
    volume=team_volume(pd.concat(pbps,ignore_index=True))
    base=pd.read_csv(out/"features.csv")
    frame,quality=build_opportunities(pd.concat(weeks,ignore_index=True),base,volume)
    if quality["matched_player_weeks"]<1000:
        raise ValueError("Insufficient team-week joins; verify team code mappings")
    frame.to_csv(out/"opportunity_features.csv",index=False)
    result=evaluate(frame)
    result["source_provenance"]=provenance
    result["quality"]=quality
    (out/"opportunity_evaluation.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=="__main__":
    main()
