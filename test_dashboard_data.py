import unittest,json
from cryptography.fernet import Fernet
from scripts.phase19_dashboard_data import decrypt_document,document_digest,validate_pair,normalized_quotes,player_summary
class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.forecast={"schema_version":1,"event_id":"e","predictions":[{"player_id":"gsis1"}]}
        self.quotes=[{"player_id":"gsis1","player_display_name":"Sample Receiver","market":"receptions","side":s,"line":line,
            "locked_projection":5.1,"bookmaker":book,"american_odds":-110,
            "book_quote_updated_after_lock":False} for s,line,book in
            (("over",4.5,"fanduel"),("under",4.5,"fanduel"),("over",5.5,"draftkings"))]
        self.comp={"schema_version":1,"matched_quotes":self.quotes,
          "summary":{"outcomes_total":3,"official_bets":0},"frozen_forecast_sha256":document_digest(self.forecast)}
    def test_encrypted_round_trip(self):
        key=Fernet.generate_key().decode()
        blob=Fernet(key.encode()).encrypt(json.dumps(self.comp).encode())
        decoded=decrypt_document(blob,key)
        validate_pair(decoded,self.forecast)
        with self.assertRaises(ValueError):decrypt_document(blob,Fernet.generate_key().decode())
        with self.assertRaises(ValueError):validate_pair(decoded,{**self.forecast,"event_id":"other"})
    def test_duplicate_over_under_not_counted_as_two_player_markets(self):
        data=normalized_quotes(self.comp)
        one=player_summary(data)
        self.assertEqual(len(data),3)
        self.assertEqual(len(one),1)
        self.assertEqual(one.iloc[0]["Distinct lines"],2)
        self.assertEqual(one.iloc[0]["Gap to median"],0.1)
    def test_research_only(self):
        data=normalized_quotes(self.comp)
        self.assertEqual(set(data.Decision),{"RESEARCH ONLY — NOT A BET"})
        self.assertEqual(self.comp["summary"]["official_bets"],0)
if __name__=="__main__":unittest.main()
