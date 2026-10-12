"""Simple private local GRIDIRON board; no live sportsbook requests."""
import io,zipfile
import streamlit as st
from scripts.phase19_dashboard_data import decrypt_document,validate_pair,normalized_quotes,player_summary

st.set_page_config(page_title="GRIDIRON | Player Props",page_icon="🏈",layout="wide")
st.markdown("""<style>
[data-testid="stAppViewContainer"]{background:#0c1119;color:#f5f6f7}
[data-testid="stSidebar"]{background:#171e29}
[data-testid="stMetric"]{background:#1b2532;padding:12px;border-radius:12px}
h1,h2,h3{letter-spacing:-.03em}
</style>""",unsafe_allow_html=True)
st.title("GRIDIRON")
st.caption("PRIVATE PLAYER PROP DASHBOARD · MODEL VS SPORTSBOOK")

st.subheader("1 · Load your Bills–Rams board")
uploaded=st.file_uploader("Drop the phase19-encrypted-private-ledger ZIP here",type=["zip","enc"],
    help="You can upload the GitHub ZIP without extracting anything.")
key=st.text_input("Your private encryption key",type="password",
    help="Paste the key you saved when Phase 19 was set up. It stays in this local app.")
if not uploaded or not key:
    st.info("Download **phase19-encrypted-private-ledger** from your completed GitHub run. Drop that ZIP above and enter your saved key. No Terminal commands or file extraction required.")
    st.markdown("[Download your encrypted ledger from GitHub →](https://github.com/coreyehh/gridiron-v3/actions/runs/38320842317)")
    st.stop()
try:
    blobs={}
    raw=uploaded.getvalue()
    if zipfile.is_zipfile(io.BytesIO(raw)):
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            # Untrusted zip: no extraction to disk, no hidden/directory traversal.
            for entry in z.infolist():
                if entry.is_dir() or entry.file_size>10_000_000:continue
                basename=entry.filename.replace("\\","/").split("/")[-1]
                if basename in ("phase19_forecasts.enc","phase19_private_comparison.enc"):
                    if basename in blobs:raise ValueError("Archive contains duplicate encrypted records")
                    blobs[basename]=z.read(entry)
    elif uploaded.name.endswith(".enc"):
        blobs["phase19_private_comparison.enc"]=raw
    else:raise ValueError("Upload your encrypted Phase 19 ledger ZIP.")
    if "phase19_private_comparison.enc" not in blobs:
        raise ValueError("Couldn't locate phase19_private_comparison.enc in the uploaded ZIP")
    comparison=decrypt_document(blobs["phase19_private_comparison.enc"],key)
    forecast=decrypt_document(blobs["phase19_forecasts.enc"],key) if "phase19_forecasts.enc" in blobs else None
    validate_pair(comparison,forecast)
    quotes=normalized_quotes(comparison)
except (ValueError,zipfile.BadZipFile) as error:
    st.error(str(error));st.stop()

st.success("Your private Bills–Rams board is open." if forecast else "Comparison board open. Forecast archive not supplied.")
if forecast:
    st.caption(f"{forecast.get('away_team','')} at {forecast.get('home_team','')} · {forecast.get('kickoff_utc','')} kickoff (UTC) · Forecast locked {forecast.get('locked_at_utc','')}")
metrics=st.columns(3)
metrics[0].metric("Player projections",len(forecast.get("predictions",[])) if forecast else "—")
metrics[1].metric("Sportsbook outcomes",len(quotes))
metrics[2].metric("Matched players",quotes["_player_id"].nunique() if len(quotes) else 0)
st.caption("Forecasts are research estimates, not approved bets. The 2026 current-form model does not yet include injuries, scheme or calibrated probabilities.")
st.subheader("2 · Model against the books")
filter1,filter2,filter3=st.columns(3)
with filter1:
    market=st.selectbox("Prop",["All markets","Receptions","Receiving yards"])
with filter2:
    players=sorted(quotes.Player.unique().tolist())
    selected=st.selectbox("Player",["All players"]+players)
with filter3:
    books=st.multiselect("Sportsbooks",sorted(quotes.Book.unique()),default=sorted(quotes.Book.unique()))
visible=quotes[quotes.Book.isin(books)].copy()
if market=="Receptions":visible=visible[visible.Market=="receptions"]
elif market=="Receiving yards":visible=visible[visible.Market=="receiving_yards"]
if selected!="All players":visible=visible[visible.Player==selected]
summ=player_summary(visible)
if summ.empty:st.info("No matching props. Adjust the filters above.")
else:
    simple=summ[["Player","Market","Projection","Median line","Gap to median","Books"]].copy()
    simple.columns=["PLAYER","PROP","GRIDIRON PROJ.","BOOK LINE (MEDIAN)","PROJ. − LINE","BOOKS"]
    st.dataframe(simple,hide_index=True,use_container_width=True,height=480)
    st.caption("Line is the median of distinct observed sportsbook thresholds. Positive gaps are model estimates above the line—not verified OVER edges or probabilities.")

with st.expander("View every sportsbook line and price"):
    detail=visible[["Player","Market","Book","Side","Line","Odds","Projection","Gap","Updated after lock","Quoted UTC"]].copy()
    st.dataframe(detail,hide_index=True,use_container_width=True,height=400)
    st.caption("Over and under quotes for the same player may repeat a line. The table above consolidates them.")
with st.expander("Audit and modeling limitations"):
    st.json({"quote_summary":comparison["summary"],"forecast_archive_verified":bool(forecast),
        "official_player_actives_verified":False,"opponent_matchup_features_included":False,
        "calibrated_probability_available":False,"qualified_bets":0})
st.caption("PRIVATE · Browser connects only to this local Mac app (127.0.0.1). Do not deploy with your key or data publicly.")
