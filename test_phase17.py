import unittest
import pandas as pd
from scripts.phase17 import latest_prior,fit_models,evaluate,VERSION
from scripts.ingest import MEASURES

def history():
 rows=[]
 for p in range(115):
  for y in (2023,2024,2025):
   for w in range(1,7):
    rows.append({"player_id":f"id{p}","season":y,"week":w,
      "position":"WR" if p%2 else "RB","receptions":float(2+p%5+w%3),
      "receiving_yards":float(15+p%12+w*3),"rushing_yards":float(p%5),
      "passing_yards":0.})
 return pd.DataFrame(rows)
class Phase17Tests(unittest.TestCase):
 def test_only_historical_rows_accepted(self):
  h=history()
  with self.assertRaises(ValueError):latest_prior(pd.concat([h,pd.DataFrame([{**h.iloc[0].to_dict(),"season":2026}])],ignore_index=True))
 def test_latest_prior_includes_final_observed_game(self):
  h=history()
  p=latest_prior(h).set_index("player_id")
  self.assertEqual(p.loc["id0","prior5_receptions"],h[h.player_id=="id0"].tail(5).receptions.mean())
 def test_models_fit(self):
  m=fit_models(history())
  self.assertIn(("RB","receptions"),m)
  self.assertIn(("WR","receiving_yards"),m)
 def test_quote_event_and_result_cannot_create_bet(self):
  h=history()
  roster=[{"player_id":"id1","player_name":"Test WR","team":"CIN","season":2026,
           "source":"test","source_ref":"test","as_of_utc":"2026-10-12T15:00:00Z"}]
  q=[{"event_id":"event1","season":2026,"home_team":"Cincinnati Bengals",
       "away_team":"Baltimore Ravens","player_display_name":"Test WR",
       "market":"receptions","kickoff_utc":"2026-10-18T17:00:00Z",
       "captured_at_utc":"2026-10-12T15:01:00Z","line":3.5}]
  rows,summary=evaluate(q,roster,h,{"2025":"hash"},"2026-10-12T15:01:00Z")
  self.assertEqual(len(rows),1)
  self.assertIsNone(rows[0]["book_line_probability"])
  self.assertEqual(rows[0]["bet_decision"],"INSUFFICIENT_DATA")
  self.assertFalse(summary["2026_current_form_included"])
 def test_same_name_team_collision_no_projection(self):
  h=history()
  roster=[{"player_id":f"id{k}","player_name":"Test WR","team":t,"season":2026,
           "source":"test","source_ref":"test","as_of_utc":"2026-10-12T15:00:00Z"} for k,t in ((1,"CIN"),(3,"BAL"))]
  q=[{"event_id":"x","season":2026,"home_team":"Cincinnati Bengals",
      "away_team":"Baltimore Ravens","player_display_name":"Test WR",
      "market":"receptions","kickoff_utc":"2026-10-18T17:00:00Z",
      "captured_at_utc":"2026-10-12T15:01:00Z"}]
  rows,_=evaluate(q,roster,h,{"2025":"hash"},"2026-10-12T15:01:00Z")
  self.assertEqual(rows,[])
if __name__=="__main__":unittest.main()
