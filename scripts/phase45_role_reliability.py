"""Phase45: source-backed pre-lock role reliability and QB competition diagnostics.

Never use target-week box scores, updated rosters or post-lock actives to
retroactively qualify bets. A roster row is NOT evidence of active status.
"""
import argparse,csv,json,math,os
from pathlib import Path
from collections import Counter,defaultdict
import pandas as pd
from scripts.phase43_remaining_week6 import check_remaining
from scripts.phase43_multimarket_forecasts import prep
from scripts.phase31_accountability import digest
from scripts.ingest import download

VERSION="phase45-role-reliability-v1"
HISTORY_START=2025

def historical_role(snapshot,raw):
    check_remaining(snapshot)
    df=prep(raw)
    # Information firewall: future/current week data NEVER contributes, even if
    # source was downloaded after fixture lock. Source publication is not attested.
    week=int(snapshot["week"])
    hist=df[(df.season==2025)|((df.season==2026)&(df.week<week))].copy()
    current=hist[hist.season==2026]
    weeklist=sorted(current.week.unique().tolist())
    if any(int(w)>=week for w in weeklist):raise ValueError("Target-week leakage")
    groups={(str(team),str(pid)):g.sort_values(["season","week"])
       for (team,pid),g in hist.groupby(["team_code","player_id"])}
    # Build each club's previous games using all observed contributors, never
    # compare a player's carry total to a QB-only subset.
    team_totals=current.groupby(["team_code","week"]).agg(
       team_pass_attempts=("attempts","sum"),
       team_rush_attempts=("carries","sum"),
       team_targets=("targets","sum")).reset_index()
    tmap={(str(x.team_code),int(x.week)):x for x in team_totals.itertuples()}
    qb_per_team=defaultdict(list)
    for p in snapshot["forecasts"]:
        if p["position"]=="QB":qb_per_team[(p["fixture_id"],p["team"])].append(p)
    audits=[];flags=Counter()
    for player in snapshot["forecasts"]:
        team,pid=str(player["team"]),str(player["player_id"])
        old=groups.get((team,pid))
        reasons=["OFFICIAL_ACTIVE_UNVERIFIED","STARTING_ROLE_UNVERIFIED",
           "HISTORICAL_USAGE_IS_NOT_GAME_DAY_PARTICIPATION",
           "PROJECTION_AND_TD_DISTRIBUTION_UNCALIBRATED"]
        recent=old[(old.season==2026)&(old.week<week)] if old is not None else pd.DataFrame()
        recent=recent.sort_values("week").tail(5)
        observed_weeks=[int(x) for x in recent.week.tolist()] if len(recent) else []
        # Count missing team-game box rows as unknown, not zero/inactive.
        team_weeks=sorted(int(w) for w in current[current.team_code==team].week.unique())[-5:]
        missing=sorted(set(team_weeks)-set(observed_weeks))
        if missing:reasons.append("PLAYER_MISSING_OBSERVED_BOX_WEEK_NOT_VERIFIED_INACTIVE")
        if len(recent)<3:reasons.append("LIMITED_CURRENT_TEAM_PLAYER_SAMPLES")
        if observed_weeks and observed_weeks[-1]<week-2:
            reasons.append("NO_RECENT_PLAYER_BOX_OBSERVATION")
        if not observed_weeks:reasons.append("NO_CURRENT_SEASON_PLAYER_OBSERVATIONS")
        historical=[]
        for x in recent.itertuples():
            t=tmap.get((team,int(x.week)))
            if t is None:continue
            at=float(x.attempts) if pd.notna(x.attempts) else None
            ca=float(x.carries) if pd.notna(x.carries) else None
            tg=float(x.targets) if pd.notna(x.targets) else None
            if at is None or ca is None or tg is None:continue
            historical.append({"week":int(x.week),"pass_attempts":at,"rush_attempts":ca,
               "targets":tg,"pass_share":round(at/float(t.team_pass_attempts),4)
                        if t.team_pass_attempts>0 else None,
               "rush_share":round(ca/float(t.team_rush_attempts),4)
                        if t.team_rush_attempts>0 else None,
               "target_share":round(tg/float(t.team_targets),4)
                        if t.team_targets>0 else None})
        usage_metric={"QB":"pass_share","RB":"rush_share","WR":"target_share",
                      "TE":"target_share"}.get(player["position"])
        values=[q[usage_metric] for q in historical if q[usage_metric] is not None]
        avg=sum(values)/len(values) if values else None
        if len(values)>=3 and avg>0:
            spread=(max(values)-min(values))/avg
            if spread>=1:reasons.append("HIGH_ROLE_SHARE_VARIATION")
        else:
            reasons.append("INSUFFICIENT_DENOMINATOR_FOR_STABLE_ROLE")
        if player["position"]=="QB":
            others=qb_per_team[(player["fixture_id"],team)]
            if len(others)>1:
                reasons.append("MULTIPLE_HISTORICAL_QB_CANDIDATES_NO_STARTER_CONFIRMED")
            if avg is None or avg<.55:
                reasons.append("LOW_OR_UNCERTAIN_PAST_TEAM_PASS_SHARE")
        pp=player["point_projections"]
        if player["position"]=="RB" and (pp.get("rushing_yards") or 0)>100:
            reasons.append("HIGH_RB_RUSH_PROJECTION_REQUIRES_ROLE_CONFIRMATION")
        if pp.get("td_count_mean")==0:
            reasons.append("ZERO_OBSERVED_TDS_DO_NOT_PROVE_ZERO_SCORE_CHANCE")
        for reason in set(reasons):flags[reason]+=1
        audits.append({"fixture_id":player["fixture_id"],"team":team,
         "player_id":pid,"player_name":player["player_name"],
         "position":player["position"],
         "recent_player_box_weeks":observed_weeks,
         "missing_box_weeks_unknown":missing,
         "historical_weekly_usage":historical,
         "usage_metric":usage_metric,"mean_prior_usage_share":round(avg,4) if avg is not None else None,
         "qb_candidates_on_same_frozen_roster":len(qb_per_team.get((player["fixture_id"],team),[]))
                        if player["position"]=="QB" else None,
         "pass_yards_projection":pp.get("passing_yards"),
         "rush_yards_projection":pp.get("rushing_yards"),
         "anytime_td_uncalibrated":pp.get("anytime_touchdown"),
         "two_plus_td_uncalibrated":pp.get("two_plus_touchdowns"),
         "three_plus_td_uncalibrated":pp.get("three_plus_touchdowns"),
         "reason_codes":sorted(set(reasons)),
         "decision":"ROLE_UNVERIFIED_NO_BET",
         "official_active_verified":False,"expected_starter_verified":False,
         "validated_probability":None,"approved_units":0})
    return audits,{"version":VERSION,"input_snapshot_sha256":snapshot["payload_sha256"],
      "week":week,"fixture_count":len(snapshot["fixtures"]),
      "forecast_count":len(snapshot["forecasts"]),
      "audited":len(audits),"risk_reason_counts":dict(sorted(flags.items())),
      "target_week_box_rows_used":0,
      "latest_2026_week_used":max(weeklist,default=None),
      "historical_source_is_point_in_time_attested":False,
      "roster_identity_source_only":True,
      "live_injury_or_official_active_feed_connected":False,
      "projected_starers_certified":0,
      "approved_bets":0,"units":0,"new_bookmaker_requests":0}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--snapshot",default="snapshots/phase43/remaining/2026-week-06-remaining-20261018T162430Z.json")
    p.add_argument("--output-dir",default="output/phase45")
    a=p.parse_args()
    snap=json.loads(Path(a.snapshot).read_text())
    folder=Path("private_data");folder.mkdir(exist_ok=True)
    records=[];provenance={}
    for yr in (2025,2026):
        data,meta=download(yr,folder);records.append(data);provenance[str(yr)]=meta["sha256"]
    audits,report=historical_role(snap,pd.concat(records,ignore_index=True))
    report["new_source_sha256"]=provenance
    result=Path(a.output_dir);result.mkdir(parents=True,exist_ok=True)
    (result/"role_quality_summary.json").write_text(json.dumps(report,indent=2))
    fields=["fixture_id","player_name","team","position","recent_player_box_weeks",
            "missing_box_weeks_unknown","usage_metric","mean_prior_usage_share",
            "qb_candidates_on_same_frozen_roster","pass_yards_projection",
            "rush_yards_projection","anytime_td_uncalibrated",
            "two_plus_td_uncalibrated","three_plus_td_uncalibrated",
            "reason_codes","decision"]
    with (result/"readable_player_role_gate.csv").open("w",newline="") as out:
        w=csv.DictWriter(out,fieldnames=fields);w.writeheader()
        for row in audits:w.writerow({c:"; ".join(map(str,row[c])) if isinstance(row[c],list)
                                       else row[c] for c in fields})
    print(f"# Phase45 Role Reliability\n\n**Player audits:** {report['audited']} across "
          f"{report['fixture_count']} matchups. **Verified starters: 0; approved bets: 0.**\n\n"
          "No future boxes or new sportsbook requests. Historical roles are observations, not confirmed starts.")
if __name__=="__main__":main()
