"""Phase 21: honest walk-forward evaluation of Phase 20 opportunities.

Predictions at week W use ONLY 2025 games and completed 2026 weeks < W.
No score from W enters any forecast. Score is used solely AFTER prediction
for error segmentation; this is not a pregame game-state model.
"""
import argparse,json,os
from pathlib import Path
import numpy as np
import pandas as pd
from scripts.ingest import download
from scripts.phase18 import fetch_schedule,completed_weeks
from scripts.phase20_opportunity import team_games,normalize,opportunity_forecast,player_forecast

VERSION="phase21-walkforward-volume-v1"
METRICS=("pass_attempts","rush_attempts","targets","receptions","receiving_yards")

def grading_environment(schedule,week,home,away):
    games=schedule[(schedule.season==2026)&(schedule.week==week)&
                   (schedule.game_type=="REG")&
                   (schedule.home_team==home)&(schedule.away_team==away)]
    if len(games)!=1:raise ValueError("Could not uniquely grade scheduled matchup")
    g=games.iloc[0]
    if pd.isna(g.home_score) or pd.isna(g.away_score):raise ValueError("Game not completed")
    total=float(g.home_score+g.away_score)
    margin=abs(float(g.home_score-g.away_score))
    # Ex-post outcome buckets are diagnostic, never features available at prediction time.
    return {"points_total":total,"margin":margin,
            "total_bucket":"high_50plus" if total>=50 else ("low_under_40" if total<40 else "mid_40_to_49"),
            "margin_bucket":"blowout_17plus" if margin>=17 else "competitive_under_17"}

def score_baseline(games,club,allowed,measure):
    current=games[(games.season==2026)&games.week.isin(allowed)&
                  (games.team_code==club)].sort_values("week")
    if current.empty:return None
    return float(current[measure].tail(3).mean())

def player_naive(previous,club,allowed):
    prior=previous[(previous.season==2026)&previous.week.isin(allowed)&
                   (previous.team_code==club)]
    weeks=sorted(prior.week.unique())[-3:]
    prior=prior[prior.week.isin(weeks)]
    count=prior.week.nunique()
    if count<1:return {}
    # Missing player rows counted as zero, not a free prediction of only healthy starters.
    gp=prior.groupby("player_id").agg(targets=("targets","sum"),
       receptions=("receptions","sum"),receiving_yards=("receiving_yards","sum"))
    return {str(pid):{m:float(row[m])/count for m in ("targets","receptions","receiving_yards")}
            for pid,row in gp.iterrows()}

def mae(records,field,model):
    vals=[abs(x[model]-x[field]) for x in records if x.get(field) is not None and x.get(model) is not None]
    return round(float(np.mean(vals)),3) if vals else None

def evaluate(history,schedule,first=2,last=18):
    players=normalize(history)
    games=team_games(players)
    results=[];team_rows=[];player_rows=[]
    # A completed week must have every game scored, otherwise don't score partial weeks.
    scored=set(completed_weeks(schedule,last+1,"2099-01-01T00:00:00Z",2026))
    for week in range(max(2,first),min(last,18)+1):
        if week not in scored:continue
        allowed={w for w in scored if w<week}
        if not allowed or max(allowed)!=week-1:continue
        matches=schedule[(schedule.season==2026)&(schedule.week==week)&(schedule.game_type=="REG")]
        for g in matches.itertuples():
            home,away=str(g.home_team),str(g.away_team)
            bucket=grading_environment(schedule,week,home,away)
            try:
                preds=opportunity_forecast(games,schedule,home,away,allowed)
            except ValueError:continue
            # actual observed THIS WEEK, never into model
            targets=games[(games.season==2026)&(games.week==week)]
            recent=players[(players.season==2025)|((players.season==2026)&players.week.isin(allowed))]
            actual_players=players[(players.season==2026)&(players.week==week)]
            for club in (home,away):
                actual=targets[targets.team_code==club]
                if len(actual)!=1:continue
                ar=actual.iloc[0]
                for metric in ("pass_attempts","rush_attempts"):
                    base=score_baseline(games,club,allowed,metric)
                    if base is None:continue
                    model=float(preds[club][metric]["projection"])
                    team_rows.append({"week":week,"team":club,"metric":metric,
                        "actual":float(ar[metric]),"baseline":base,"model":model,**bucket})
                try:
                    model_players=player_forecast(recent,preds[club],allowed,club)
                except ValueError:continue
                baseline_players=player_naive(recent,club,allowed)
                actual_map=actual_players[actual_players.team_code==club].set_index("player_id")
                for p in model_players:
                    pid=p["player_id"]
                    # Include absence from stats feed as zero with explicit unverified availability caveat.
                    ar=actual_map.loc[pid] if pid in actual_map.index else None
                    for metric,field in (("targets","targets_projection"),
                                         ("receptions","receptions_projection"),
                                         ("receiving_yards","receiving_yards_projection")):
                        model=float(p[field])
                        base=baseline_players.get(pid,{}).get(metric)
                        if base is None:continue
                        actual_val=float(ar[metric]) if ar is not None else 0.
                        player_rows.append({"week":week,"team":club,"player_id":pid,
                           "metric":metric,"actual":actual_val,"baseline":base,
                           "model":model,"was_in_stats_row":ar is not None,**bucket})
            results.append({"week":week,"home":home,"away":away,**bucket})
    if not team_rows:raise ValueError("Insufficient complete walk-forward team-game samples")
    def metrics(rows):
        out=[]
        for field in ("pass_attempts","rush_attempts","targets","receptions","receiving_yards"):
            subset=[r for r in rows if r["metric"]==field]
            if not subset:continue
            mm=mae(subset,"actual","model");bb=mae(subset,"actual","baseline")
            out.append({"market":field,"observations":len(subset),
              "model_mae":mm,"baseline_mae":bb,
              "mae_delta_model_minus_baseline":round(mm-bb,3),
              "model_wins":mm<bb})
        return out
    t=metrics(team_rows);p=metrics(player_rows)
    slices=[]
    for criterion in ("total_bucket","margin_bucket"):
        for category in sorted(set(r[criterion] for r in team_rows)):
            rows=[r for r in team_rows if r[criterion]==category and r["metric"]=="pass_attempts"]
            if not rows:continue
            slices.append({"dimension":criterion,"bucket":category,"team_games":len(rows),
              "pass_attempts_model_mae":mae(rows,"actual","model"),
              "pass_attempts_baseline_mae":mae(rows,"actual","baseline")})
    return {"status":"completed_walk_forward_research","model_version":VERSION,
      "tested_weeks":sorted(set(g["week"] for g in results)),
      "matchups_evaluated":len(results),"team_metric_rows":len(team_rows),
      "player_metric_rows":len(player_rows),
      "team_accuracy":t,"player_accuracy":p,"environment_slices":slices,
      "incomplete_weeks_excluded":True,"target_week_stats_in_forecast":False,
      "environment_bucket_uses_postgame_score_for_grading_only":True,
      "historical_data_downloaded_after_games":True,
      "point_in_time_feed_publication_verified":False,
      "actual_player_inactives_verified":False,
      "team_opponent_heuristics_tuned_on_holdout":False,
      "predictive_scenario_probabilities_calibrated":False,
      "live_sportsbook_lines_used":False,"bets_qualified":0,"roi_verified":False}

def markdown(result):
    lines=["# GRIDIRON Phase 21 — Walk-forward accuracy audit","",
       f"**{result['matchups_evaluated']} completed games · 2026 weeks {', '.join(map(str,result['tested_weeks']))}**",
       "","## Does Phase 20 beat a 3-game trailing average?","",
       "| Opportunity | Samples | Phase 20 MAE | Simple baseline MAE | Improvement? |",
       "|:--|--:|--:|--:|:--|"]
    for row in result["team_accuracy"]+result["player_accuracy"]:
        lines.append(f"| {row['market']} | {row['observations']} | {row['model_mae']:.2f} | {row['baseline_mae']:.2f} | {'Yes' if row['model_wins'] else 'No'} |")
    lines+=["","## Error by **actual** game environment (diagnostic only)","",
       "| Segment | Team-games | Phase 20 pass attempts MAE | Baseline MAE |",
       "|:--|--:|--:|--:|"]
    for s in result["environment_slices"]:
        lines.append(f"| {s['bucket']} | {s['team_games']} | {s['pass_attempts_model_mae']:.2f} | {s['pass_attempts_baseline_mae']:.2f} |")
    lines+=["",
       "**Important:** Game environment (total points and margin) is determined AFTER the game for diagnostic error segmentation, never used to predict. This is not calibrated game-state variance yet.",
       "Player rows include zero actual production when a historically projected player is absent from the game's player-week feed; inactives are not verified. Baseline opportunities use actual prior weeks only.",
       "No current bookmaker lines or prices; these are errors in unit counts and yards, NOT betting probabilities, EV or certified ROI.",
       ""]
    return "\n".join(lines)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--first-week",type=int,default=2)
    p.add_argument("--last-week",type=int,default=18)
    p.add_argument("--summary",default="output/phase21_accuracy.json")
    a=p.parse_args()
    if a.first_week<2 or a.last_week>18 or a.last_week<a.first_week:
        p.error("Expected 2026 regular-season weeks 2..18")
    folder=Path("private_data");folder.mkdir(exist_ok=True)
    schedule,sch_hash=fetch_schedule(folder)
    frames=[]; hashes={"schedule":sch_hash}
    for year in (2025,2026):
        data,meta=download(year,folder);frames.append(data);hashes[str(year)]=meta["sha256"]
    report=evaluate(pd.concat(frames,ignore_index=True),schedule,a.first_week,a.last_week)
    report["sources"]=hashes
    path=Path(a.summary);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2))
    table=markdown(report);print(table)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write(table)
if __name__=="__main__":main()
