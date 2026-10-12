"""Phase 9: audited RB on-field passing-play participation proxies.

IMPORTANT: Being on field on a passing play does NOT prove a route was run.
Do not rename these features 'routes', 'routes run', or 'TPRR'.
Source: nflverse participation, NGS <=2022; FTN 2023+ (CC BY-SA 4.0).
"""
import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

BASE="https://github.com/nflverse/nflverse-data/releases/download/pbp_participation/pbp_participation_{}.parquet"
STATS=["prior5_receptions","prior5_receiving_yards","prior5_rushing_yards","prior5_passing_yards",
       "prior3_receptions","prior3_receiving_yards","prior3_rushing_yards","prior3_passing_yards"]
OPP=["prior_team_pass_attempts_5","prior_rb_targets_5","prior_rb_target_share_5",
     "prior_rb_catch_rate_5","prior_rb_yards_per_target_5"]
NEW=["prior_rb_pass_play_snaps_5","prior_rb_targets_per_pass_play_snap_5"]
MARKETS=[("receptions",.75),("receiving_yards",7.5)]

def fetch_participation(year,folder):
    url=BASE.format(year)
    dest=folder/("pbp_participation_%s.parquet"%year)
    with urlopen(Request(url,headers={"User-Agent":"GRIDIRON-v3/1.0"}),timeout=180) as stream:
        with dest.open("wb") as out: shutil.copyfileobj(stream,out)
    df=pd.read_parquet(dest,columns=["nflverse_game_id","play_id","offense_players"])
    if df.empty: raise ValueError("Empty participation file: "+str(year))
    if df.duplicated(["nflverse_game_id","play_id"]).any():
        raise ValueError("Participation duplicate game-play key: "+str(year))
    return df,{"season":year,"rows":int(len(df)),"source":url,
              "sha256":hashlib.sha256(dest.read_bytes()).hexdigest(),
              "credit":"FTN Data via nflverse" if year>=2023 else "NFL NextGenStats via nflverse"}

def split_offense_ids(ids):
    if not isinstance(ids,str) or not ids.strip(): return []
    # Official feed uses semicolon-separated GSIS identifiers.
    members=[s.strip() for s in re.split(r"[;,]",ids) if s.strip()]
    if any(not re.fullmatch(r"00-\\d{7}",p) for p in members):
        raise ValueError("Unexpected player identifier encoding in offense_players")
    return members

def on_field_pass_snaps(pbp,participation,rb_ids,year):
    needed={"game_id","play_id","season","week","posteam","pass_attempt","season_type"}
    if not needed.issubset(pbp):
        raise ValueError("PBP missing fields "+str(sorted(needed-set(pbp))))
    passplays=pbp[(pbp.season==year)&(pbp.season_type=="REG")&
                  (pd.to_numeric(pbp.pass_attempt,errors="coerce")==1)&pbp.posteam.notna()].copy()
    if passplays.duplicated(["game_id","play_id"]).any():
        raise ValueError("PBP duplicate game-play key")
    both=passplays.merge(participation[["nflverse_game_id","play_id","offense_players"]],
                         left_on=["game_id","play_id"],right_on=["nflverse_game_id","play_id"],
                         how="left",validate="one_to_one")
    coverage=float(both.offense_players.notna().mean()) if len(both) else 0
    if coverage<.75:
        raise ValueError("Pass-play participation coverage too low: %.3f"%coverage)
    counts={}
    for row in both[["week","offense_players"]].itertuples(index=False,name=None):
        week,players=row
        if not isinstance(players,str): continue
        for player in split_offense_ids(players):
            if player in rb_ids:
                key=(year,int(week),player)
                counts[key]=counts.get(key,0)+1
    result=pd.DataFrame([(s,w,p,n) for (s,w,p),n in counts.items()],
                        columns=["season","week","player_id","rb_on_field_pass_plays"])
    return result,{"season":year,"passing_plays":int(len(both)),
                   "participation_coverage":round(coverage,4),
                   "rb_player_week_counts":int(len(result))}

def make_features(base,playerstats,onfield):
    keys=["season","week","player_id"]
    if not set(keys+["targets","season_type"]).issubset(playerstats.columns):
        raise ValueError("Missing player-stat identifiers or targets")
    weekly=playerstats[playerstats.season_type=="REG"][keys+["targets"]].copy()
    if weekly.duplicated(keys).any():raise ValueError("Duplicate reg-season player rows")
    matched=weekly.merge(onfield,on=keys,how="left",validate="one_to_one")
    # Zero on-field passing snaps can be real, but missing participation
    # is not automatically zero: keep it missing until coverage confirmed.
    matched["rb_targets_per_onfield_pass_play"]=np.where(
        matched.rb_on_field_pass_plays>0,
        pd.to_numeric(matched.targets,errors="coerce")/matched.rb_on_field_pass_plays,np.nan)
    matched=matched.sort_values(["player_id","season","week"])
    grouped=matched.groupby("player_id",sort=False)
    matched["prior_rb_pass_play_snaps_5"]=grouped.rb_on_field_pass_plays.transform(
        lambda s:s.shift(1).rolling(5,min_periods=1).mean())
    matched["prior_rb_targets_per_pass_play_snap_5"]=grouped.rb_targets_per_onfield_pass_play.transform(
        lambda s:s.shift(1).rolling(5,min_periods=1).mean())
    out=base.merge(matched[keys+NEW],on=keys,how="left",validate="one_to_one")
    return out

def fit_compare(rows,market,threshold):
    x=rows[(rows.prior_position=="RB")&(rows.prior_observations>=3)&
           (rows["prior5_"+market]>=threshold)&rows[market].notna()&
           rows.prior_team_pass_attempts_5.notna()&
           rows.prior_rb_pass_play_snaps_5.notna()].copy()
    train=x[x.season.between(2021,2023)]
    valid=x[x.season==2024]
    test=x[x.season==2025]
    out={"market":market,"train_n":len(train),"validation_n":len(valid),"test_n":len(test)}
    if min(len(train),len(valid),len(test))<50:
        return dict(out,status="insufficient_samples")
    fitted={}
    for name,cols in [("phase8_on_same_players",STATS+OPP),
                      ("phase9_onfield_proxy",STATS+OPP+NEW)]:
        best=None
        for alpha in (1.,10.,100.):
            estimator=make_pipeline(SimpleImputer(strategy="constant",fill_value=0),
                                    StandardScaler(),Ridge(alpha=alpha))
            estimator.fit(train[cols],train[market])
            score=mean_absolute_error(valid[market],np.maximum(0,estimator.predict(valid[cols])))
            if best is None or score<best[0]:best=(score,alpha)
        estimator=make_pipeline(SimpleImputer(strategy="constant",fill_value=0),
                                StandardScaler(),Ridge(alpha=best[1]))
        both=pd.concat([train,valid])
        estimator.fit(both[cols],both[market])
        p=np.maximum(0,estimator.predict(test[cols]))
        fitted[name]={"mae":round(float(mean_absolute_error(test[market],p)),5),
                      "rmse":round(float(np.sqrt(mean_squared_error(test[market],p))),5),
                      "alpha":best[1]}
    old=fitted["phase8_on_same_players"]["mae"]
    new=fitted["phase9_onfield_proxy"]["mae"]
    return dict(out,status="evaluated",models=fitted,
                improvement_pct=round(100*(old-new)/old,2),
                improved=bool(new<old))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default="output")
    parser.add_argument("--seasons",type=int,nargs="+",default=[2021,2022,2023,2024,2025])
    args=parser.parse_args()
    folder=Path(args.output)
    history=pd.concat([pd.read_parquet(folder/("stats_player_week_%s.parquet"%yr))
                       for yr in args.seasons],ignore_index=True)
    rb_ids=set(history.loc[history.position=="RB","player_id"].dropna().astype(str))
    pbp=[];participations=[];quality=[]
    for yr in args.seasons:
        part,source=fetch_participation(yr,folder)
        field=pd.read_parquet(folder/("play_by_play_%s.parquet"%yr),
                             columns=["game_id","play_id","season","week","posteam","pass_attempt","season_type"])
        agg,qa=on_field_pass_snaps(field,part,rb_ids,yr)
        pbp.append(agg);participations.append(source);quality.append(qa)
    onfield=pd.concat(pbp,ignore_index=True)
    opportunities=pd.read_csv(folder/"opportunity_features.csv")
    merged=make_features(opportunities,history,onfield)
    merged.to_csv(folder/"participation_features.csv",index=False)
    output={"status":"2025_heldout_pass_play_onfield_proxy",
            "evaluated_at_utc":datetime.now(timezone.utc).isoformat(),
            "train_years":[2021,2022,2023],"validation_year":2024,"test_year":2025,
            "participation_sources":participations,"quality":quality,
            "terminology":"on-field passing-play appearances; NOT confirmed routes run",
            "missing_routes":True,"pregame_roster_complete":False,
            "historical_odds_available":False,"betting_roi_validated":False,
            "results":[fit_compare(merged,m,t) for m,t in MARKETS]}
    (folder/"participation_evaluation.json").write_text(json.dumps(output,indent=2))
    print(json.dumps(output,indent=2))

if __name__=="__main__":main()
