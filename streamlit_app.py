import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Heatseeker Lite", layout="wide")
st.title("Heatseeker Lite — Free Forever")

# Sidebar
ticker = st.sidebar.selectbox("Ticker", ["SPY", "QQQ", "IWM", "AAPL", "TSLA", "NVDA", "AMD", "META"])
spot = st.sidebar.number_input("Current price", value=683.39, step=0.1, format="%.2f")

# Realistic mock data centered on current price
np.random.seed(42)
strikes = np.round(np.arange(spot-70, spot+71, 1), 2)  # $1 increments, wider range
dist = np.abs(strikes - spot)
oi = np.maximum(4000, 35000 * np.exp(-dist/30)).astype(int)

df = pd.DataFrame({"strike": strikes, "oi": oi})
df["gamma"] = 0.4 / (df["strike"] * 0.2 * np.sqrt(0.08))
df["gex"] = -df["oi"] * df["gamma"] * spot*spot * 0.01 * np.random.uniform(0.6, 1.4, len(df))

gex = df.groupby("strike")["gex"].sum().reset_index()
king = gex.loc[gex["gex"].idxmax(), "strike"]

# Chart
fig = go.Figure()
fig.add_trace(go.Bar(
    x=gex["strike"], y=gex["gex"]/1e6,
    marker_color=["limegreen" if x > 0 else "crimson" for x in gex["gex"]],
    name="GEX"
))
fig.add_vline(x=spot, line_color="white", line_dash="dot", annotation_text=f"Spot ${spot:.2f}")
fig.add_vline(x=king, line_color="gold", line_width=8, annotation_text=f"KING NODE ${king:.1f}")
fig.update_layout(
    title=f"{ticker} → King Node ${king:.1f}",
    xaxis_title="Strike Price", yaxis_title="Net GEX ($ millions)",
    height=700, template="plotly_dark"
)
st.plotly_chart(fig, use_container_width=True)

# Results
c1, c2 = st.columns(2)
c1.metric("KING NODE", f"${king:.1f}", delta=f"{spot-king:+.2f}")
c2.metric("Total OI", f"{df['oi'].sum():,} contracts")

st.success(f"Dealers are magnetized to **${king:.1f}** right now")
