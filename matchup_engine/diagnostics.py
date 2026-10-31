"""Paired prediction diagnostics; no model selection using held-out results."""
import numpy as np
import pandas as pd

def paired_diagnostics(baseline,enhanced):
    keys=["season","game_id"]
    a=baseline.set_index(keys).sort_index()
    b=enhanced.set_index(keys).sort_index()
    if not a.index.equals(b.index):
        raise ValueError("Models must be evaluated on identical games")
    for target in ("actual_home_win","actual_margin","actual_total"):
        if not a[target].equals(b[target]):
            raise ValueError(f"Ground truth differs for {target}")
    rows=[]
    for season in sorted(a.index.get_level_values("season").unique()):
        aa=a.loc[season]
        bb=b.loc[season]
        rows.append({
            "season":int(season),"games":int(len(aa)),
            "delta_brier":float(np.mean((bb.home_win_probability-bb.actual_home_win)**2-
                                         (aa.home_win_probability-aa.actual_home_win)**2)),
            "delta_margin_mae":float(np.mean(abs(bb.pred_margin-bb.actual_margin)-
                                              abs(aa.pred_margin-aa.actual_margin))),
            "delta_total_mae":float(np.mean(abs(bb.pred_total-bb.actual_total)-
                                             abs(aa.pred_total-aa.actual_total))),
        })
    return pd.DataFrame(rows)
