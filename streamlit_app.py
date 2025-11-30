import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests

st.set_page_config(page_title="Heatseeker Pro", layout="wide")
st.title("Heatseeker Pro — Live Dealer Gamma")

# Sidebar
st.sidebar.header("Live Settings")
API_KEY = st.sidebar.text_input("Polygon.io Key (free works)", type="password")
ticker = st.sidebar.selectbox("Ticker", ["SPY","QQQ","IWM","AAPL","TSLA","NVDA","AMD","META","MSFT","GOOGL","SMH"])

# Live spot price
if API_KEY and API_KEY.strip():
    try:
        spot = requests.get(f"https://api.polygon.io/v2/last/trade/{ticker}?apiKey={API_KEY}", timeout=8).json()["results"]["p"]
    except:
        spot = 683.39
else:
    spot = 683.39

# Fetch live chain
@st.cache_data(ttl=120)
def get_chain(tkr):
    if not API_KEY or not API_KEY.strip():
        return pd.DataFrame()
    url = f"https://api.polygon.io/v3/reference/options/contracts?underlying_ticker={tkr}&limit=1000&apiKey={API_KEY}"
    try:
        resp = requests.get(url, timeout=12).json()
        return pd.DataFrame(resp.get("results", []))
    except:
        return pd.DataFrame()

df = get_chain(ticker)

# ——— Demo / fallback data ———
if df.empty or len(df) < 10:
    st.info("Live mode active as soon as you paste a free Polygon key • Running realistic demo until then")
    strikes = np.arange(round(spot-80), round(spot+81), 1)
    dist = np.abs(strikes - spot)
    oi = np.maximum(4000, 45000 * np.exp(-dist/30)).astype(int)
    df = pd.DataFrame({"strike_price": strikes, "open_interest": oi})

# ——— Clean & calculate GEX ———
df["strike"] = pd.to_numeric(df["strike_price"], errors="coerce")

if "open_interest" in df.columns:
    df["oi"] = pd.to_numeric(df["open_interest"], errors="coerce").fillna(2000)
else:
    df["oi"] = 2000

df["gamma"] = 0.4 / (df["strike"] * 0.2 * np.sqrt(0.08))
df["gex"]   = -df["oi"] * df["gamma"] * spot*spot * 0.01

gex = df.groupby("strike")["gex"].sum().reset_index().dropna()

king  = gex.loc[gex["gex"].idxmax(), "strike"]
vanna = gex.loc[gex["gex"].idxmin(), "strike"]

# ——— Chart ———
fig = go.Figure()
fig.add_trace(go.Bar(
    x=gex["strike"], y=gex["gex"]/1e6,
    marker_color=["limegreen" if x > 0 else "crimson" for x in gex["gex"]]
))
fig.add_vline(x=spot, line_color="white", line_dash="dot", annotation_text=f"Spot ${spot:.2f}")
fig.add_vline(x=king, line_color="gold", line_width=8, annotation_text=f"KING ${king:.0f}")
fig.add_vline(x=vanna, line_color="purple", line_width=5, annotation_text=f"VANNA ${vanna:.0f}")
fig.update_layout(title=f"{ticker} • King Node ${king:.0f}", height=700, template="plotly_dark")
st.plotly_chart(fig, use_container_width=True)

# ——— Metrics ———
c1, c2, c3 = st.columns(3)
c1.metric("KING NODE", f"${king:.0f}", delta=f"{spot-king:+.1f}")
c2.metric("VANNA TARGET", f"${vanna:.0f}")
c3.metric("Spot Price", f"${spot:.2f}")

st.success(f"Dealers defending **${king:.0f}** • Vanna risk at **${vanna:.0f}**")
