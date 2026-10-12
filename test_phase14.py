import unittest
from scripts.phase14 import join_quote,build_board,settle_official_pick,digest
Q={"event_id":"e1","season":2026,"kickoff_utc":"2026-10-18T17:00:00Z",
"quoted_at_utc":"2026-10-17T12:00:00Z","captured_at_utc":"2026-10-17T12:01:00Z",
"player_display_name":"Alex Sample Jr.","home_team":"CIN","away_team":"BAL",
"market":"receptions","side":"over","line":3.5,"american_odds":-110,"bookmaker":"fanduel"}
R=[{"player_name":"Alex Sample","player_id":"known","team":"CIN","season":2026,
"source":"test","source_ref":"fixture","as_of_utc":"2026-10-16T12:00:00Z"}]
P=[{"event_id":"e1","player_id":"known","market":"receptions",
"point_projection":4.,"model_version":"test","input_snapshot_sha256":"abcd",
"created_at_utc":"2026-10-17T10:00:00Z"}]
class Phase14Tests(unittest.TestCase):
 def test_identity_and_forecast_join_still_no_bet(self):
  r=join_quote(Q,R,P)
  self.assertEqual(r["player_id"],"known")
  self.assertEqual(r["projection"],4.)
  self.assertEqual(r["decision"],"INSUFFICIENT_DATA")
  self.assertIsNone(r["model_probability"])
 def test_duplicate_name_is_ambiguous(self):
  self.assertEqual(join_quote(Q,R+[{**R[0],"player_id":"different"}],P)["identity_status"],"AMBIGUOUS")
 def test_future_roster_not_used(self):
  self.assertEqual(join_quote(Q,[{**R[0],"as_of_utc":"2026-10-18T12:00:00Z"}],P)["identity_status"],"UNRESOLVED")
 def test_post_quote_projection_is_rejected(self):
  self.assertEqual(join_quote(Q,R,[{**P[0],"created_at_utc":"2026-10-17T12:00:01Z"}])["reason"],"projection_after_quote")
 def test_kickoff_guard(self):
  with self.assertRaises(ValueError):join_quote({**Q,"captured_at_utc":"2026-10-18T18:00:00Z"},R,P)
 def test_missing_explicit_season(self):
  q=dict(Q);q.pop("season")
  with self.assertRaises(ValueError):join_quote(q,R,P)
 def test_board_qualified_zero(self):
  b=build_board({"quotes":[Q]},R,P)
  self.assertEqual(b["bets_qualified"],0)
  self.assertEqual(len(digest(b)),64)
 def test_official_grading(self):
  p={"status":"OFFICIAL","signed_snapshot_sha256":"valid","locked_at_utc":"2026-10-17T12:00:00Z","kickoff_utc":"2026-10-18T17:00:00Z","market":"receptions","side":"over","line":3,"american_odds":-110}
  result={"official":True,"source_ref":"test"}
  self.assertEqual(settle_official_pick({**p,"status":"LEAN"},4,result)["grade"],"EXCLUDED_NOT_OFFICIAL")
  self.assertEqual(settle_official_pick(p,3,result)["grade"],"PUSH")
  self.assertEqual(settle_official_pick(p,4,result)["grade"],"WIN")
  self.assertEqual(settle_official_pick(p,2,result)["net_units"],-1.)
  self.assertEqual(settle_official_pick(p,4,None)["grade"],"UNGRADED")
  self.assertEqual(settle_official_pick({**p,"locked_at_utc":"2026-10-18T18:00:00Z"},4,result)["grade"],"UNGRADED")
if __name__=="__main__":unittest.main()
