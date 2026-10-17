"""Phase39: official inactives observation + encrypted FanDuel evidence archive.

Explicitly paid live mode: one FanDuel event, encrypt normalized original
player quotes with Fernet from a GitHub Secret; ONLY ciphertext may be published.
No authenticated GSIS inactive records available from public landing page yet.
"""
import argparse,hashlib,json,os,re,ssl
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request,urlopen
from cryptography.fernet import Fernet,InvalidToken
from scripts.phase31_accountability import verify_snapshot,canonical
from scripts.phase35_fanduel_portfolio import BOOK
from scripts.phase32_market_matching import discover,selected_fixture
from scripts.live_odds_smoke import SPORT,MARKETS,fetch_json
from scripts.live_market import dt,normalize
from scripts.phase25_market_gate import validate_offer
from scripts.phase28_snap_participation import name_key
from scripts.phase32_market_matching import matched_forecasts

VERSION="phase39-official-source-and-encrypted-market-archive-v1"
OFFICIAL="https://www.nfl.com/inactives/"
MAX_HTML=1_500_000
MAX_ARCHIVE_ROWS=10000

class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__();self.skip=0;self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style"):self.skip+=1
    def handle_endtag(self,tag):
        if tag in ("script","style") and self.skip:self.skip-=1
    def handle_data(self,value):
        if not self.skip:self.parts.append(value)
def official_observation(html_bytes,source_url=OFFICIAL):
    """Useful source-status signal; no automatic player status qualification."""
    if urlparse(source_url).scheme!="https" or urlparse(source_url).hostname!="www.nfl.com":
        raise ValueError("Untrusted official page origin")
    if not isinstance(html_bytes,bytes) or len(html_bytes)>MAX_HTML:raise ValueError("Invalid official page")
    parser=VisibleText();parser.feed(html_bytes.decode("utf-8",errors="replace"))
    text=" ".join(parser.parts)
    text=" ".join(text.split())
    waiting=bool(re.search(r"check back soon|no inactive reports|not available yet",text,re.I))
    return {"status":"OFFICIAL_PAGE_HAS_NO_REPORTS" if waiting else
                "OFFICIAL_PAGE_CONTENT_NOT_PLAYER_ID_VERIFIED",
       "source_sha256":hashlib.sha256(html_bytes).hexdigest(),
       "bytes_received":len(html_bytes),
       "no_reports_message_detected":waiting,
       "verified_individual_inactives":0,
       "verified_individual_actives":0,
       "fixture_gsis_mapping_available":False,
       "not_listed_does_not_imply_active":True,
       "game_day_player_evidence_usable":False}

def fetch_official_page(fetcher=None):
    captured=datetime.now(timezone.utc).isoformat()
    result={"source":"nfl.com/inactives","retrieved_at_utc":captured,
      "status":"UNAVAILABLE","verified_individual_inactives":0,
      "verified_individual_actives":0}
    try:
        if fetcher:
            content,location,status=fetcher(OFFICIAL)
        else:
            request=Request(OFFICIAL,headers={"User-Agent":"GRIDIRON-evidence-research/1.0"})
            with urlopen(request,context=ssl.create_default_context(),timeout=12) as response:
                location=response.geturl();status=response.status;content=response.read(MAX_HTML+1)
        if status!=200:raise ValueError("Not HTTP 200")
        obs=official_observation(content,location)
        result.update(obs);result["retrieved_over_tls"]=fetcher is None
        if fetcher is not None:result["test_transport_only"]=True
    except (OSError,TimeoutError,ValueError,TypeError,UnicodeError) as e:
        result["status"]="UNAVAILABLE_OR_UNVERIFIABLE"
    return result

def verify_cipher_key(key):
    if not isinstance(key,str) or not key:raise ValueError("QUOTE_ARCHIVE_KEY required")
    try:
        raw=__import__("base64").urlsafe_b64decode(key.encode("ascii"))
        if len(raw)!=32:raise ValueError("Expected 32-byte Fernet key")
        Fernet(key.encode("ascii"))
    except (ValueError,TypeError,__import__("binascii").Error):
        raise ValueError("Invalid QUOTE_ARCHIVE_KEY")
    return key.encode("ascii")

def encrypt_fanduel_event(snapshot,event,quotes,captured_at,key):
    """Authentic in-run provider response required externally; verify it here.
    Return ciphertext and public-safe counts only; no plaintext persisted.
    """
    verify_snapshot(snapshot)
    selected=selected_fixture(snapshot,event)
    captured=dt(captured_at)
    lock=dt(snapshot["created_at_utc"].replace("+00:00","Z"))
    kickoff=dt(event["commence_time"])
    if not lock<captured<kickoff:raise ValueError("Not pregame")
    if not isinstance(quotes,list) or len(quotes)>MAX_ARCHIVE_ROWS:raise ValueError("Unbounded archive")
    known,_=matched_forecasts(snapshot,selected)
    count={"quotes_received":0,"valid_offer_sides":0,"unique_name_matches":0,
       "unmatched_name_sides":0,"unsupported_or_invalid_sides":0}
    matches=set();valid=[]
    for q in quotes:
        count["quotes_received"]+=1
        if q.get("bookmaker")!=BOOK or q.get("event_id")!=event["id"]:
            raise ValueError("Mixed bookmaker or event")
        # The sportsbook's own update must not predate the immutable model
        # forecast lock. A later API capture alone does not prove this.
        if dt(q["quoted_at_utc"]) < lock:
            raise ValueError("Bookmaker quote timestamp predates forecast lock")
        try:validate_offer(q,captured_at)
        except (TypeError,ValueError,KeyError):
            count["unsupported_or_invalid_sides"]+=1;continue
        count["valid_offer_sides"]+=1
        if name_key(q.get("player_display_name")) in known:
            matches.add(name_key(q["player_display_name"]))
        else:count["unmatched_name_sides"]+=1
        valid.append(q)
    count["unique_name_matches"]=len(matches)
    record={"version":VERSION,"event":event,"captured_at_utc":captured_at,
            "snapshot_sha256":snapshot["payload_sha256"],"quotes":valid}
    plain=canonical(record).encode("utf-8")
    cipher=Fernet(verify_cipher_key(key)).encrypt(plain)
    # Hash of ciphertext differs each run because encryption is randomized.
    return cipher,{"status":"ENCRYPTED_FANDUEL_ARCHIVE_READY",
      "matched_fixture":selected["id"],"snapshot_sha256":snapshot["payload_sha256"],
      "captured_at_utc":captured_at,"counts":count,
      "encrypted_archive_sha256":hashlib.sha256(cipher).hexdigest(),
      "encryption":"Fernet AES128-CBC+HMAC SHA256",
      "raw_quote_artifacts":False,"player_level_quote_publication":False,
      "archive_key_in_output":False,
      "provider_player_id_verification":False,
      "official_active_source_verified":False,
      "real_line_calibrated_probability_available":False,
      "accepted_fanduel_sgp_quote_available":False,
      "qualified_bets":0}

def decrypt_archive(cipher,key):
    """ONLY on user's trusted local/private machine. Never in GitHub log."""
    try:return json.loads(Fernet(verify_cipher_key(key)).decrypt(cipher))
    except InvalidToken:raise ValueError("Wrong key or corrupted archive") from None

def live_once(snapshot,key,archive_key,region="us",event_id=""):
    verify_cipher_key(archive_key) # Do not spend credits if private storage unavailable
    events=discover(key,snapshot,event_id)
    if not events:return None,{"status":"NO_FUTURE_FROZEN_MATCHUP","paid_request":False}
    e=events[0]
    payload,quota=fetch_json("/v4/sports/"+SPORT+"/events/"+e["id"]+"/odds",
        {"regions":region,"markets":",".join(MARKETS),
         "bookmakers":BOOK,"oddsFormat":"american"},key)
    if any(payload.get(k)!=e.get(k) for k in ("id","commence_time","home_team","away_team")):
        raise ValueError("Odds provider changed event")
    if any(b.get("key")!=BOOK for b in payload.get("bookmakers",[])):
        raise ValueError("Response contains other bookmakers")
    stamp=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    quotes=normalize(payload,stamp)
    cipher,public=encrypt_fanduel_event(snapshot,e,quotes,stamp,archive_key)
    public["paid_request"]=True
    public["quota_remaining"]=quota.get("x-requests-remaining")
    return cipher,public

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--snapshot",default="snapshots/phase31/2026-week-06.json")
    p.add_argument("--output-dir",default="output/phase39")
    p.add_argument("--live",action="store_true")
    p.add_argument("--probe-official",action="store_true")
    p.add_argument("--region",choices=["us","us2","ca"],default="us")
    p.add_argument("--event-id",default="")
    a=p.parse_args()
    snapshot=json.loads(Path(a.snapshot).read_text());verify_snapshot(snapshot)
    official=fetch_official_page() if a.probe_official else {
       "status":"NOT_REQUESTED","verified_individual_inactives":0,
       "verified_individual_actives":0}
    public={"version":VERSION,"season":snapshot["season"],"week":snapshot["week"],
       "frozen_predictions":len(snapshot["forecasts"]),"games":len(snapshot["fixtures"]),
       "official_inactives":official,
       "market_archive":{"status":"NOT_REQUESTED","paid_request":False},
       "qualified_singles":0,"qualified_2_3_4_5_leg_parlays":0,"units_allocated":0,
       "real_line_calibration_verified":False,
       "game_day_official_active_records_verified":False}
    out=Path(a.output_dir);out.mkdir(parents=True,exist_ok=True)
    if a.live:
        if not os.environ.get("ODDS_API_KEY"):raise ValueError("ODDS_API_KEY secret required")
        cipher,market=live_once(snapshot,os.environ["ODDS_API_KEY"],
               os.environ.get("QUOTE_ARCHIVE_KEY"),a.region,a.event_id)
        public["market_archive"]=market
        if cipher is not None:
            dest=out/"fanduel_archive.fernet"
            dest.write_bytes(cipher)
            os.chmod(dest,0o600)
    (out/"evidence_summary.json").write_text(json.dumps(public,indent=2))
    lines=("# GRIDIRON Phase39 — Real source & encrypted FanDuel evidence\n\n"
       f"**Official NFL inactive page:** {official['status']}; **verified player statuses: 0**.\n\n"
       f"**Encrypted FanDuel archive:** {public['market_archive']['status']}.\n\n"
       f"**Qualified singles: 0 | parlays: 0 | units: 0.**\n\n"
       "No active player is inferred from page omission. No raw lines or secret keys "
       "are printed. Live mode uses one paid event only and requires QUOTE_ARCHIVE_KEY.\n")
    print(lines)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write(lines)
if __name__=="__main__":main()
