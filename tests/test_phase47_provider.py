import unittest
from scripts.phase47_provider import normalize
SCHEDULE={"evt1":{"season":2026,"week":7,"kickoff_utc":"2026-10-22T20:15:00-04:00"}}
IDS={("evt1","Test Runner"):"player-1"}
def payload(**overrides):
    p={"timestamp":"2026-10-22T19:00:00-04:00","data":{"id":"evt1","commence_time":"2026-10-22T20:15:00-04:00","bookmakers":[{"key":"fanduel","markets":[{"key":"player_rush_attempts","outcomes":[{"description":"Test Runner","name":"Over","point":14.5,"price":-110},{"description":"Test Runner","name":"Under","point":14.5,"price":-110}]}]}]}}
    p.update(overrides)
    return p
class ProviderTests(unittest.TestCase):
    def test_two_sides(self): self.assertEqual(tuple(map(len,normalize(payload(),IDS,SCHEDULE))),(2,0))
    def test_unresolved_player(self): self.assertEqual(tuple(map(len,normalize(payload(),{},SCHEDULE))),(0,2))
    def test_post_kickoff(self): self.assertEqual(tuple(map(len,normalize(payload(timestamp="2026-10-22T21:00:00-04:00"),IDS,SCHEDULE))),(0,2))
    def test_mismatched_kickoff(self):
        p=payload();p["data"]["commence_time"]="2026-10-22T19:15:00-04:00"
        with self.assertRaises(ValueError): normalize(p,IDS,SCHEDULE)
    def test_dedup(self):
        p=payload();p["data"]["bookmakers"].append(p["data"]["bookmakers"][0])
        self.assertEqual(tuple(map(len,normalize(p,IDS,SCHEDULE))),(2,0))
    def test_stale(self): self.assertEqual(tuple(map(len,normalize(payload(timestamp="2026-10-20T19:00:00-04:00"),IDS,SCHEDULE))),(0,2))
if __name__=="__main__": unittest.main()
