"""Transparent, static weekly GRIDIRON matchup dashboard.

Shows preliminary model outputs, not verified bookmaker odds or approved bets.
"""
from pathlib import Path
from html import escape
import pandas as pd

COLUMNS=[("gameday","Date"),("away_team","Away"),("home_team","Home"),
         ("projected_winner","Projected winner"),("home_win_probability","Home win %"),
         ("fair_home_spread","Fair home spread"),("pred_total","Projected total"),
         ("projected_home_points","Home points"),("projected_away_points","Away points")]

def render_matchup_dashboard(board, metrics=None, title="GRIDIRON — Matchup Board"):
    if board.empty:
        raise ValueError("Cannot render empty matchup board")
    required={key for key,_ in COLUMNS}|{"game_id"}
    missing=required-set(board.columns)
    if missing:
        raise ValueError(f"Dashboard missing fields: {sorted(missing)}")
    if board.game_id.duplicated().any():
        raise ValueError("Duplicate game IDs")
    if "model_status" in board.columns:
        statuses=set(board.model_status.dropna().astype(str))
        if any("PRELIMINARY" not in status for status in statuses):
            raise ValueError("Unrecognized model status")
    headers="".join(f"<th>{escape(label)}</th>" for _,label in COLUMNS)
    rows=[]
    for _,r in board.sort_values(["gameday","game_id"]).iterrows():
        cells=[]
        for key,_ in COLUMNS:
            value=r[key]
            if key=="home_win_probability":
                shown=f"{float(value)*100:.1f}%"
            elif key in ("fair_home_spread","pred_total","projected_home_points","projected_away_points"):
                shown=f"{float(value):+.1f}" if key=="fair_home_spread" else f"{float(value):.1f}"
            else:
                shown=str(value)
            cells.append(f"<td>{escape(shown)}</td>")
        rows.append("<tr>"+"".join(cells)+"</tr>")
    metric_html=""
    if metrics:
        entries=[]
        for key in ("snapshot_games","graded_games","pending_games","winner_accuracy",
                    "brier","log_loss","margin_mae","total_mae"):
            if key in metrics:
                val=metrics[key]
                shown="Pending" if val is None else f"{val:.3f}" if isinstance(val,float) else str(val)
                entries.append(f"<div><strong>{escape(key.replace('_',' ').title())}</strong><span>{escape(shown)}</span></div>")
        metric_html='<section class="metrics">'+''.join(entries)+'</section>'
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title><style>
:root{{color-scheme:dark}}body{{margin:0;background:#0b0d10;color:#f3f5f7;font:15px system-ui,Arial,sans-serif}}
main{{max-width:1480px;margin:auto;padding:32px 24px}}h1{{font-size:32px;letter-spacing:-.04em}}
.notice{{border-left:4px solid #ff6b19;background:#23180f;padding:16px;margin:22px 0;line-height:1.6}}
table{{border-collapse:collapse;width:100%;min-width:920px}}.scroll{{overflow:auto;border:1px solid #30343c;border-radius:10px}}
th{{background:#20242b;color:#ff9b63;text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:.05em}}
th,td{{padding:13px 12px;border-bottom:1px solid #30343c;white-space:nowrap}}
tr:nth-child(even){{background:#151920}}.metrics{{display:flex;flex-wrap:wrap;gap:12px;margin:24px 0}}
.metrics div{{background:#20242b;padding:14px 18px;border-radius:8px;display:grid;gap:6px}}
.metrics strong{{font-size:12px;color:#ff9b63}}.metrics span{{font-size:20px}}
footer{{color:#aeb6c1;margin-top:24px;font-size:13px}}</style></head><body><main>
<h1>{escape(title)}</h1>
<div class="notice"><strong>PRELIMINARY MODEL — NOT OFFICIAL WAGERS.</strong><br>
No verified injuries, starting lineups, sportsbook prices, or positive expected value are implied.
Win percentages are historical baseline model outputs, not independently calibrated live betting probabilities.</div>
{metric_html}<div class="scroll"><table><thead><tr>{headers}</tr></thead><tbody>
{''.join(rows)}</tbody></table></div>
<footer>Fair home spread is negative when the home team is favored. All displayed values are model projections.</footer>
</main></body></html>"""

def write_matchup_dashboard(board,output,metrics=None):
    target=Path(output)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(render_matchup_dashboard(board,metrics),encoding="utf-8")
    return target
