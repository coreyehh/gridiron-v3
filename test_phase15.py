import unittest
import pandas as pd
from scripts.phase15 import snapshot_rows,report,team_code
from scripts.phase14 import identity

class Phase15Tests(unittest.TestCase):
 def frame(self):
  return pd.DataFrame([
   {"season":2026,"team":"CIN","full_name":"Example Player Jr.","gsis_id":"00-0000001"},
   {"season":2026,"team":"BAL","full_name":"Example Player Jr.","gsis_id":"00-0000002"},
   {"season":2026,"team":"CIN","full_name":"Another Player","gsis_id":"00-0000003"}])
 def test_real_source_schema_normalization(self):
  rows=snapshot_rows(self.frame(),2026,"2026-10-12T21:00:00Z","nflverse-fixture","123")
  self.assertEqual(len(rows),3)
  self.assertFalse(rows[0]["official_game_day_active_verified"])
  self.assertEqual(team_code("JAC"),"JAX")
  self.assertEqual(report(rows,"fixture","123","2026-10-12T21:00:00Z")["players_with_ids"],3)
 def test_missing_ids_fail_closed(self):
  with self.assertRaises(ValueError):snapshot_rows(self.frame().drop(columns="gsis_id"),2026,"2026-10-12T21:00:00Z","fixture","abc")
 def test_cross_season_rejected(self):
  with self.assertRaises(ValueError):snapshot_rows(self.frame(),2025,"2026-10-12T21:00:00Z","fixture","abc")
 def test_name_team_temporal_guard(self):
  sample=self.frame()
  # Use an unambiguous name for this timestamp test; same-name opponents must be rejected.
  sample.loc[sample["team"]=="BAL","full_name"]="Different Player"
  rows=snapshot_rows(sample,2026,"2026-10-12T21:00:00Z","fixture","abc")
  base={"season":2026,"home_team":"CIN","away_team":"BAL","player_display_name":"Example Player",
        "captured_at_utc":"2026-10-12T22:00:00Z"}
  status,pid=identity(base,rows)
  self.assertEqual(status,"IDENTITY_MATCHED_NOT_ACTIVE_VERIFIED")
  self.assertEqual(pid,"00-0000001")
  old={**base,"captured_at_utc":"2026-10-12T20:00:00Z"}
  self.assertEqual(identity(old,rows)[0],"UNRESOLVED")
 def test_same_name_on_opposing_teams_is_ambiguous(self):
  rows=snapshot_rows(self.frame(),2026,"2026-10-12T21:00:00Z","fixture","abc")
  q={"season":2026,"home_team":"CIN","away_team":"BAL",
     "player_display_name":"Example Player Jr.","captured_at_utc":"2026-10-12T22:00:00Z"}
  self.assertEqual(identity(q,rows)[0],"AMBIGUOUS")
 def test_multiple_player_ids_rejected(self):
  f=pd.concat([self.frame(),pd.DataFrame([{"season":2026,"team":"CIN",
   "full_name":"Example Player","gsis_id":"00-9999999"}])],ignore_index=True)
  rows=snapshot_rows(f,2026,"2026-10-12T21:00:00Z","fixture","abc")
  q={"season":2026,"home_team":"CIN","away_team":"BAL",
      "player_display_name":"Example Player","captured_at_utc":"2026-10-12T22:00:00Z"}
  self.assertEqual(identity(q,rows)[0],"AMBIGUOUS")
if __name__=="__main__":unittest.main()
