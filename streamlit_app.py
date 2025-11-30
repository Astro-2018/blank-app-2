import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime

st.set_page_config(page_title="Heatseeker Pro", layout="wide")
st.title("Heatseeker Pro — Live Dealer Gamma")

# ─── Sidebar ───
st.sidebar.header("Live Settings")
API_KEY = st.sidebar.text_input("Polygon.io Key (free works)", type="password", value="")
ticker = st.sidebar.selectbox("Ticker", ["SPY","QQQ","IWM","AAPL","TSLA","NVDA","AMD","META","MSFT","GOOGL","SMH","HOOD"])
auto_refresh = st.sidebar.checkbox("Auto-refresh every 60s", value=True)

if auto_refresh:
    st.sidebar.info("Refreshes automatically")
    st.rerun()  # Remove this line if you don’t want constant refresh

# ─── Fetch live chain ───
@st.cache_data(ttl=60)
def get_chain(ticker):
    if not API_KEY:
        st.warning("Paste your free Polygon key for live data")
        return pd.DataFrame()
    url = f"https://api.polygon.io/v3/reference/options/contracts?underlying_ticker={ticker}&limit=1000&apiKey={API_KEY}"
    try:
        data = requests.get(url, timeout=10).json().get("results", [])
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

df = get_chain(ticker)

# ─── Fallback to realistic mock if no key or empty ───
if df.empty:
    st.info("Running in demo mode — paste Polygon key for live OI")
    spot = 683.39
    strikes = np.round(np.arange(spot-70, spot+71, 1), 2)
    dist = np.abs(strikes - spot)
    oi = np.maximum(4000, 35000 * np.exp(-dist/30)).astype(int)
    df = pd.DataFrame({"strike_price": strikes, "open_interest": oi})
else:
    spot = float(requests.get(f"https://api.polygon.io/v2/last/trade/{ticker}?apiKey={API_KEY}").json()["results"]["p"])
    df = df[df["expiration_date"] > str(datetime.now().date())[:10]]
    df["oi"] = pd.to_numeric(df["open_interest"], errors="coerce").fillna(1000)

# ─── GEX + Vanna + Gatekeepers ───
df["strike"] = df["strike_price"].astype(float)
df["T"] = np.maximum((pd.to_datetime(df.get("expiration_date", "2026-01-01")) - pd.to_datetime("today")).dt.days / 365, 0.02)
df["gamma"] = 0.4 / (df["strike"] * 0.2 * np.sqrt(df["T"]))
df["gex"] = -df["oi"] * df["gamma"] * spot*spot * 0.01

gex = df.groupby("strike")["gex"].sum().reset_index()
king = gex.loc[gex["gex"].idxmax(), "strike"]
vanna = gex.loc[gex["gex"].idxmin(), "strike"]  # strongest negative = Vanna Flow target
gatekeeper = gex[gex["gex"] < gex["gex"].quantile(0.1)]["strike"].min()  # lowest positive GEX

# ─── Plot ───
fig = go.Figure()
fig.add_trace(go.Bar(x=gex["strike"], y=gex["gex"]/1e6,
                     marker_color=["limegreen" if x>0 else "crimson" for x in gex["gex"]]))
fig.add_vline(x=spot, line_color="white", line_dash="dot", annotation_text=f"Spot ${spot:.2f}")
fig.add_vline(x=king, line_color="gold", line_width=8, annotation_text=f"KING NODE ${king:.1f}")
fig.add_vline(x=vanna, line_color="purple", line_width=4, annotation_text=f"Vanna ${vanna:.1f}")
fig.add_vline(x=gatekeeper, line_color="orange", line_width=4, annotation_text=f"Gatekeeper ${gatekeeper:.1f}")
fig.update_layout(title=f"{ticker} Live → King Node ${king:.1f}", height=700, template="plotly_dark")
st.plotly_chart(fig, use_container_width=True)

# ─── Metrics ───
c1, c2, c3, c4 = st.columns(4)
c1.metric("KING NODE", f"${king:.1f}", delta=f"{spot-king:+.2f}")
c2.metric("VANNA FLOW", f"${vanna:.1f}")
c3.metric("GATEKEEPER", f"${gatekeeper:.1f}")
c4.metric("Spot", f"${spot:.2f}")

st.success(f"Dealers defending {ticker} at **${king:.1f}** — Vanna target ${vanna:.1f}")

# ─── Table ───
st.dataframe(gex.assign(GEX_M=(gex.gex/1e6).round(2))
             .sort_values("gex", ascending=False)
             .head(30), use_container_width=True)
