"""Phase 23: walk-forward player-role challenger using observed target shares.

No proprietary tracking feeds, route participation, official active statuses or
opponent coverage rates are available in this version. Role is inferred from
prior target opportunities ONLY. Every sample uses completed weeks < target.
The challenger must beat the frozen Phase20 forecast on identical player-game
rows; no sportsbook probabilities or EV are produced.
"""
import argparse,json,os
from pathlib import Path
import numpy as np
import pandas as pd
from scripts.ingest import download
from scripts.phase18 import fetch_schedule,completed_weeks
from scripts.phase20_opportunity import normalize,team_games,opportunity_forecast,player_forecast

VERSION="phase23-role-share-challenger-v1"
# Fixed BEFORE evaluating candidate; no post-hoc parameter optimization.
RECENT_WEIGHT=0.45
MIN_TEAM_GAMES=3
ROLE_STRENGTH=100.0

def role_forecast(prior,team_pass_attempts,allowed,club):
    """Estimate player opportunities using recent versus longer-run target share.

    Missing weekly player rows are counted as zero targets but never interpreted
    as confirmed inactive. Fractional weights adapt to recent role changes.
    """
    f=normalize(prior)
    recent=f[(f.season==2026)&f.week.isin(allowed)&(f.team_code==club)]
    old=f[(f.season==2025)&(f.team_code==club)]
    team=team_games(recent).sort_values("week")
    weeks=sorted(team.week.astype(int).tolist())
    if len(weeks)<MIN_TEAM_GAMES:return []
    weeks5=weeks[-5:];weeks2=weeks[-2:]
    den5=float(team.loc[team.week.isin(weeks5),"pass_attempts"].sum())
    den2=float(team.loc[team.week.isin(weeks2),"pass_attempts"].sum())
    if den5<=0 or den2<=0:raise ValueError("No meaningful team pass opportunities")
    hist=recent[recent.week.isin(weeks5)]
    result=[]
    for pid,group in hist.groupby("player_id"):
        # Don't predict players not seen in the latest 3 games; unverified
        # active status still applies, and this is a historical heuristic.
        last_week=int(group.week.max())
        if last_week<weeks[-3]:continue
        x=group
        five=float(x.targets.sum())/den5
        two=float(x.loc[x.week.isin(weeks2),"targets"].sum())/den2
        if five<=0 and two<=0:continue
        base=old[old.player_id==pid].sort_values("week").tail(5)
        base_team=team_games(old[old.week.isin(sorted(old.week.unique())[-5:])])
        denom_old=float(base_team.pass_attempts.sum()) if len(base_team) else 0.
        old_share=float(base.targets.sum())/denom_old if denom_old else five
        n=float(x.targets.sum())
        # Global team-year past share is a weak prior, not an active assumption.
        reliability=n/(n+6.)
        share=(1-reliability)*(.75*five+.25*old_share)+reliability*((1-RECENT_WEIGHT)*five+RECENT_WEIGHT*two)
        total_targets=float(x.targets.sum())
        prior_targets=float(base.targets.sum())
        c=float(x.receptions.sum());y=float(x.receiving_yards.sum())
        c0=float(base.receptions.sum());y0=float(base.receiving_yards.sum())
        rate=(c+.2*c0+2*.68)/(total_targets+.2*prior_targets+2)
        ypt=(y+.2*y0+2*7)/(total_targets+.2*prior_targets+2)
        t=max(0.,float(team_pass_attempts)*share)
        result.append({"player_id":str(pid),"team":club,
           "targets":t,"receptions":t*rate,"receiving_yards":t*ypt,
           "last_observed_week":last_week,"targets_last2_share":two,
           "targets_last5_share":five,"share":share,
           "availability_verified":False})
    return result

def backtest(history,schedule,first=4,last=18):
    stats=normalize(history)
    games=team_games(stats)
    done=set(completed_weeks(schedule,min(19,last+1),"2099-01-01T00:00:00Z",2026))
    rows=[]
    for wk in range(max(4,first),min(18,last)+1):
        if wk not in done:continue
        allowed={x for x in done if x<wk}
        if max(allowed,default=0)!=wk-1:continue
        prior=stats[(stats.season==2025)|((stats.season==2026)&stats.week.isin(allowed))]
        schedule_week=schedule[(schedule.season==2026)&(schedule.week==wk)&(schedule.game_type=="REG")]
        current=stats[(stats.season==2026)&(stats.week==wk)]
        for matchup in schedule_week.itertuples():
            home,away=str(matchup.home_team),str(matchup.away_team)
            try:projs=opportunity_forecast(games,schedule,home,away,allowed)
            except ValueError:continue
            for club in (home,away):
                try:
                    p20=player_forecast(prior,projs[club],allowed,club)
                    p23=role_forecast(prior,projs[club]["pass_attempts"]["projection"],allowed,club)
                except ValueError:continue
                p20map={r["player_id"]:r for r in p20}
                p23map={r["player_id"]:r for r in p23}
                truth=current[current.team_code==club].set_index("player_id")
                # Same player cohort for all comparisons, including players with
                # zero production in box score; no active knowledge inferred.
                ids=sorted(set(p20map)|set(p23map))
                for pid in ids:
                    if pid not in p20map:continue
                    base=p20map[pid];new=p23map.get(pid)
                    found=pid in truth.index
                    for metric,source in (("targets","targets_projection"),
                             ("receptions","receptions_projection"),
                             ("receiving_yards","receiving_yards_projection")):
                        actual=float(truth.loc[pid,metric]) if found else 0.
                        rows.append({"week":wk,"team":club,"player_id":pid,
                           "metric":metric,"actual":actual,
                           "phase20":float(base[source]),
                           "phase23":float(new[metric]) if new else 0.,
                           "included_in_week_box":bool(found),
                           "role_challenger_has_recent_observation":new is not None})
    if not rows:raise ValueError("No valid historical evaluation sample")
    summary=[]
    for metric in ("targets","receptions","receiving_yards"):
        selected=[x for x in rows if x["metric"]==metric]
        m20=np.mean([abs(x["actual"]-x["phase20"]) for x in selected])
        m23=np.mean([abs(x["actual"]-x["phase23"]) for x in selected])
        summary.append({"metric":metric,"observations":len(selected),
           "phase20_mae":round(float(m20),4),"phase23_mae":round(float(m23),4),
           "phase23_improves":bool(m23<m20),
           "difference":round(float(m23-m20),4)})
    # Explicit diagnostics for injury/role-change uncertainty.
    slices=[]
    for name,subset in (("seen_in_box",[x for x in rows if x["included_in_week_box"]]),
                        ("not_seen_in_box",[x for x in rows if not x["included_in_week_box"]]),
                        ("recent_role",[x for x in rows if x["role_challenger_has_recent_observation"]]),
                        ("stale_role",[x for x in rows if not x["role_challenger_has_recent_observation"]])):
        for metric in ("targets","receptions","receiving_yards"):
            xs=[r for r in subset if r["metric"]==metric]
            if not xs:continue
            slices.append({"cohort":name,"metric":metric,"n":len(xs),
              "phase20_mae":round(float(np.mean([abs(r["phase20"]-r["actual"]) for r in xs])),3),
              "phase23_mae":round(float(np.mean([abs(r["phase23"]-r["actual"]) for r in xs])),3)})
    # Strict: target, catches, and yard MAE must all improve, but any positive
    # backtest signal remains research-only until new prospective data exists.
    improved=all(x["phase23_improves"] for x in summary)
    return {"version":VERSION,"weeks":sorted(set(r["week"] for r in rows)),
      "player_games":len(rows)//3,"rows":len(rows),
      "metrics":summary,"availability_diagnostics":slices,
      "candidate_passes_backtest_gates":improved,
      "production_player_champion":"phase23_candidate" if improved else "phase20",
      "role_proxy":"recent prior-game target share only",
      "routes_or_snaps_verified":False,"actives_verified":False,
      "opponent_coverage_modeled":False,"source_publication_asof_verified":False,
      "sportsbook_probs_calibrated":False,"official_bets":0}

def markdown(result):
    lines=["# GRIDIRON Phase 23 — Player role accuracy audit","",
      f"**{result['player_games']} player-games · completed 2026 weeks {', '.join(map(str,result['weeks']))}**","",
      "## Does adaptive target share beat Phase 20?","",
      "| Metric | Player-games | Phase 20 MAE | Phase 23 MAE | Improves? |",
      "|:--|--:|--:|--:|:--|"]
    for r in result["metrics"]:
        lines.append(f"| {r['metric']} | {r['observations']} | {r['phase20_mae']:.2f} | {r['phase23_mae']:.2f} | {'Yes' if r['phase23_improves'] else 'No'} |")
    lines+=["","## Role availability diagnostics","",
      "| Cohort | Metric | N | Phase 20 MAE | Phase 23 MAE |",
      "|:--|:--|--:|--:|--:|"]
    for r in result["availability_diagnostics"]:
        lines.append(f"| {r['cohort']} | {r['metric']} | {r['n']} | {r['phase20_mae']:.2f} | {r['phase23_mae']:.2f} |")
    lines+=["",f"**Historical comparison gate:** {'passed' if result['candidate_passes_backtest_gates'] else 'FAILED'}; production player champion: **{result['production_player_champion']}**.",
      "Player rows absent from a target week's statistics are graded zero; this is NOT proof of confirmed inactive status.",
      "This phase uses prior target shares, NOT routes/snap counts, verified injuries, personnel, or opponent coverage. No sportsbook odds, calibrated prop probabilities or validated profitable bets.",""]
    return "\n".join(lines)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--first-week",type=int,default=4)
    p.add_argument("--last-week",type=int,default=18)
    p.add_argument("--output",default="output/phase23_role_audit.json")
    a=p.parse_args()
    if not (4<=a.first_week<=a.last_week<=18):p.error("Expected weeks 4..18")
    folder=Path("private_data");folder.mkdir(exist_ok=True)
    schedule,sha=fetch_schedule(folder)
    frames=[];sources={"schedule":sha}
    for season in (2025,2026):
        df,meta=download(season,folder);frames.append(df);sources[str(season)]=meta["sha256"]
    report=backtest(pd.concat(frames,ignore_index=True),schedule,a.first_week,a.last_week)
    report["source_sha256"]=sources
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2))
    msg=markdown(report);print(msg)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write(msg)
if __name__=="__main__":main()
