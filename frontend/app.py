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
from metrics import render_metrics

st.set_page_config(page_title="Strategy Backtester", layout="wide")

st.title("📊 Strategy Research & Backtesting Tool")

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

## from test_frontend_portfolio_mean_reversion.py 
payload = { #what is needed to pass into strategies 
    "tickers": params['assets'],
    "start_date": params['start_date'].isoformat(),
    "end_date": params['end_date'].isoformat(),
    "initial_capital": float(10000),
    "strategy_name": params['strategy'],
    "strategy_params": {
        "bb_window": int(params['params']['bb_window']),
        "bb_std": float(2.0),
        "rsi_window": int(14),
        "rsi_entry": float(params['params']['rsi_low']), 
        "rsi_exit": float(params['params']['rsi_high']),
    },
}
tickers = params['assets']
# st.subheader("Request Body")
# st.json(payload)

if st.button("Run Portfolio Backtest"):
    if not tickers:
        st.warning("Please select at least one ticker.")
    else:
        response = requests.post(
            "http://127.0.0.1:8000/backtest/run-portfolio",
            json=payload
        )

        if response.status_code != 200:
            st.error(f"API error: {response.status_code}")
            try:
                st.json(response.json())
            except Exception:
                st.write(response.text)
        else:
            data = response.json()
            render_metrics(data)
            render_charts(data)



            
# # -------------------------
# # Run Pipeline
# # -------------------------
# # if st.button("Run Backtest"):

# #     df = load_data(params["ticker"], params["start"], params["end"])
# #     df = compute_indicators(df, params)
# #     df = generate_signals(df, params)

# #     results = run_backtest(df)
# #     metrics = compute_metrics(results)

# #     results["data"] = df
# #     results["metrics"] = metrics

# #     # -------------------------
# #     # Layout
# #     # -------------------------
# #     col1, col2 = st.columns([3, 1])

# #     with col1:
#         # render_charts(results)

# #     with col2:
# #         render_metrics(results)