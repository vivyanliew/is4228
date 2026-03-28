import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# from data import load_data
# from indicators import compute_indicators
# from strategy import generate_signals
# from backtest import run_backtest
# from metrics import compute_metrics

from sidebar import render_sidebar
from charts import render_charts
# from metrics import render_metrics

st.set_page_config(page_title="Strategy Backtester", layout="wide")

st.title("📊 Strategy Research & Backtesting Tool")


dates = pd.date_range(start="2023-01-01", periods=100)

df = pd.DataFrame({
    "Date": dates,
    "Close": np.cumsum(np.random.randn(100)) + 100,
})

df["signal"] = 0
df.loc[::15, "signal"] = 1   # fake buys
df.loc[7::15, "signal"] = -1 # fake sells

equity_curve = df["Close"].copy()

mock_results = {
    "data": df.set_index("Date"),
    "equity_curve": equity_curve,
    "trades": []
}
# -------------------------
# Sidebar Inputs
# -------------------------
params = render_sidebar()

if not params["run"]:
    st.info(" Configure your strategy in the sidebar and click 'Run Backtest'")
if params["run"]:
    st.success("Backtest triggered ")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Configuration")
        st.json(params)

    with col2:
        st.subheader("Summary")
        st.write(f"**Tier:** {params['tier']}")
        st.write(f"**Strategy:** {params['strategy']}")
        st.write(f"**Assets:** {params['assets']}")

render_charts(mock_results) ##Move this line to below when merging with metrics
# -------------------------
# Run Pipeline
# -------------------------
# if st.button("Run Backtest"):

#     df = load_data(params["ticker"], params["start"], params["end"])
#     df = compute_indicators(df, params)
#     df = generate_signals(df, params)

#     results = run_backtest(df)
#     metrics = compute_metrics(results)

#     results["data"] = df
#     results["metrics"] = metrics

#     # -------------------------
#     # Layout
#     # -------------------------
#     col1, col2 = st.columns([3, 1])

#     with col1:
        # render_charts(results)

#     with col2:
#         render_metrics(results)