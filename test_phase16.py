import unittest
from scripts.phase16 import team_id, players, audit, TEAMS

ASOF="2026-10-12T20:00:00Z"
ROSTER=[
 {"season":2026,"team":"CIN","player_name":"Alex Example Jr.","player_id":"a","source":"nflverse","source_ref":"fixture","as_of_utc":ASOF},
 {"season":2026,"team":"BAL","player_name":"Alex Example Jr.","player_id":"b","source":"nflverse","source_ref":"fixture","as_of_utc":ASOF},
 {"season":2026,"team":"CIN","player_name":"Unique Example","player_id":"c","source":"nflverse","source_ref":"fixture","as_of_utc":ASOF}]
Q={"event_id":"abc","season":2026,"home_team":"Cincinnati Bengals","away_team":"Baltimore Ravens","player_display_name":"Unique Example","market":"receptions","side":"over","line":3.5,"american_odds":-110,"bookmaker":"fanduel","quoted_at_utc":"2026-10-12T20:00:15Z","captured_at_utc":"2026-10-12T20:02:00Z","kickoff_utc":"2026-10-18T17:00:00Z"}
RA={"season":2026,"source_sha256":"test","retrieved_at_utc":ASOF}
class Phase16Tests(unittest.TestCase):
 def test_teams(self):
  self.assertEqual(len(TEAMS),32)
  self.assertEqual(len(set(TEAMS.values())),32)
  self.assertEqual(team_id("Cincinnati Bengals"),"CIN")
  self.assertEqual(team_id("JAC"),"JAX")
  self.assertIsNone(team_id("Unknown"))
 def test_grouped_outcomes(self):
  a=players([Q,{**Q,"market":"receiving_yards","side":"under"}],ROSTER)
  self.assertEqual((a["unique_event_players"],a["quote_outcome_count"],a["identity_matched"]),(1,2,1))
  self.assertEqual(a["bets_qualified"],0)
 def test_ambiguous(self):
  self.assertEqual(players([{**Q,"player_display_name":"Alex Example"}],ROSTER)["ambiguous"],1)
 def test_unknown_team(self):
  self.assertEqual(players([{**Q,"away_team":"Unknown"}],ROSTER)["unmapped_event_teams"],1)
 def test_missing_player(self):
  self.assertEqual(players([{**Q,"player_display_name":"No Match"}],ROSTER)["unresolved"],1)
 def test_no_retroactive_rosters(self):
  with self.assertRaises(ValueError):
   audit(ROSTER,{**RA,"retrieved_at_utc":"2026-10-12T20:03:00Z"},[Q],{})
 def test_no_postkickoff(self):
  with self.assertRaises(ValueError):
   audit(ROSTER,RA,[{**Q,"captured_at_utc":"2026-10-18T18:00:00Z"}],{})
 def test_aggregate_only(self):
  a=audit(ROSTER,RA,[Q],{"bookmakers":["fanduel"]})
  self.assertEqual(a["identity_matched"],1)
  self.assertEqual(a["bets_qualified"],0)
  self.assertNotIn("Unique Example",str(a))
 def test_inconsistent_event(self):
  self.assertEqual(players([Q,{**Q,"home_team":"Chicago Bears"}],ROSTER)["inconsistent_events"],1)
if __name__=="__main__":unittest.main()
