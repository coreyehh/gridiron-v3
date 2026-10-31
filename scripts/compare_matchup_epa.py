"""Compare historical matchup models on paired EPA-complete seasons."""
import argparse
import json
from pathlib import Path
from matchup_engine.ingest import fetch_completed_games
from matchup_engine.data import load_games
from matchup_engine.features import make_training_frame
from matchup_engine.epa_data import load_epa_games
from matchup_engine.epa_features import add_epa_features
from matchup_engine.compare import compare_models
from matchup_engine.diagnostics import paired_diagnostics

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--start-season",type=int,default=2018)
    parser.add_argument("--through-season",type=int,default=2025)
    parser.add_argument("--output-dir",default="artifacts/matchup-epa")
    args=parser.parse_args()
    if args.start_season>=args.through_season:
        parser.error("start-season must precede through-season")
    out=Path(args.output_dir)
    out.mkdir(parents=True,exist_ok=True)
    games=fetch_completed_games(through_season=args.through_season)
    games=games.loc[games.season.between(args.start_season,args.through_season)].copy()
    frame=make_training_frame(games)
    aggregates=load_epa_games(range(args.start_season,args.through_season+1))
    enriched=add_epa_features(frame,aggregates)
    predictions,metrics=compare_models(enriched)
    diagnostics=paired_diagnostics(predictions['baseline'],predictions['epa'])
    diagnostics.to_csv(out/'paired_diagnostics_by_season.csv',index=False)
    for name,p in predictions.items():
        p.to_csv(out/f"{name}_predictions.csv",index=False)
    (out/"metrics.json").write_text(json.dumps(metrics,indent=2)+"\n")
    print(json.dumps(metrics,indent=2))

if __name__=="__main__":
    main()
