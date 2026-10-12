"""Private local dashboard. Launch with: python -m streamlit run dashboard.py --server.address 127.0.0.1"""
import streamlit as st
from scripts.phase19_dashboard_data import decrypt_document,validate_pair,normalized_quotes,player_summary

st.set_page_config(page_title="GRIDIRON | Private Prop Board",page_icon="🏈",layout="wide")
st.markdown("""<style>
[data-testid="stAppViewContainer"]{background:#0e121a;color:#f3f4f6}
[data-testid="stSidebar"]{background:#161c27}
[data-testid="stMetric"]{background:#1d2633;padding:14px;border-radius:12px;border:1px solid #364150}
h1,h2,h3{letter-spacing:-.03em}
</style>""",unsafe_allow_html=True)
st.title("GRIDIRON / Private Player Prop Board")
st.caption("PHASE 19 · LOCKED PRE-GAME PROJECTIONS × AUTHENTIC BOOKMAKER QUOTES")
st.warning("RESEARCH ONLY — not a betting recommendation. No injury/actives verification, opponent matchup adjustment, line probability or proven EV.")
with st.sidebar:
    st.header("Unlock your private ledger")
    compfile=st.file_uploader("phase19_private_comparison.enc",type=["enc"],key="comparisons")
    forefile=st.file_uploader("phase19_forecasts.enc (recommended)",type=["enc"],key="forecasts")
    secret=st.text_input("GRIDIRON_ARCHIVE_KEY",type="password",
        help="Enter the encryption key saved to your password manager. Never post it to GitHub or chat.")
    st.caption("Runs locally on your Mac. Encrypted artifacts are decrypted into this local session only.")

if compfile is None or not secret:
    st.info("Download and extract the encrypted ledger from your Phase 19 run, then upload the .enc files and enter your secret key.")
    st.markdown("[Open Phase 19 run → Artifacts → phase19-encrypted-private-ledger](https://github.com/coreyehh/gridiron-v3/actions/runs/38320842317)")
    st.stop()
try:
    comparison=decrypt_document(compfile.getvalue(),secret)
    forecast=decrypt_document(forefile.getvalue(),secret) if forefile else None
    validate_pair(comparison,forecast)
    quotes=normalized_quotes(comparison)
    base=player_summary(quotes)
except ValueError as ex:
    st.error(str(ex));st.stop()

st.success("Encrypted research ledger decrypted locally" +
    (" — forecast/comparison archive integrity verified." if forecast else " — upload the matching forecast archive to verify its integrity."))
c1,c2,c3,c4=st.columns(4)
c1.metric("Locked forecasts",len(forecast.get("predictions",[])) if forecast else "—")
c2.metric("Comparable quote outcomes",len(quotes))
c3.metric("Players with quotes",quotes["_player_id"].nunique() if len(quotes) else 0)
c4.metric("Qualified bets",0)
audit=comparison.get("summary",{})
a,b,c=st.columns(3)
a.metric("All available outcomes",audit.get("outcomes_total","—"))
b.metric("Existing prices observed after lock",audit.get("existing_price_observed_after_lock","—"))
c.metric("Book prices updated after lock",audit.get("updated_after_lock","—"))
st.caption("The bookmaker may have last updated a line before the model's forecast lock, even though the price was collected afterward.")
if forecast:
    st.caption(f"Event: {forecast.get('away_team','')} at {forecast.get('home_team','')} | Kickoff UTC: {forecast.get('kickoff_utc','')} | Forecast lock UTC: {forecast.get('locked_at_utc','')}")
with st.sidebar:
    st.header("Filters")
    market=st.selectbox("Market",["All"]+sorted(quotes.Market.unique().tolist()))
    books=st.multiselect("Sportsbooks",sorted(quotes.Book.unique()),default=sorted(quotes.Book.unique()))
    player=st.selectbox("Player",["All"]+sorted(quotes.Player.unique().tolist()))
    fresh=st.checkbox("Book updated after lock only",value=False)
view=quotes.copy()
if market!="All":view=view[view.Market==market]
if player!="All":view=view[view.Player==player]
view=view[view.Book.isin(books)]
if fresh:view=view[view["Updated after lock"]]
st.subheader("Player-by-player projections")
st.caption("One row per player × market. Gaps use the median DISTINCT sportsbook line, not repeated over/under sides. These are not ranked picks.")
st.dataframe(player_summary(view),hide_index=True,use_container_width=True,height=450)
st.subheader("All individual sportsbook outcomes")
st.caption("Quotes can repeat across books and over/under sides; they are not independent player opportunities.")
st.dataframe(view.drop(columns="_player_id"),hide_index=True,use_container_width=True,height=450)
with st.expander("Audit metadata and limitations"):
    st.json({"matchup":{k:forecast.get(k) for k in ("home_team","away_team","kickoff_utc","locked_at_utc","model_version")} if forecast else "No forecast file",
        "forecast_archive_verified":bool(forecast),"quote_summary":audit,
        "calibrated_probabilities":False,"official_actives_verified":False,"qualified_bets":0})
st.caption("Keep your decryption key private. This viewer does not request odds or contact external services.")
