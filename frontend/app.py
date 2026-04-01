import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from api import build_payload

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
    st.success("Backtest triggered")

    # Build payload
    payload = build_payload(params)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Configuration")
        st.json(payload)

    with col2:
        st.subheader("Summary")
        st.write(f"**Tier:** {params['tier']}")
        st.write(f"**Strategy:** {params['strategy']}")
        st.write(f"**Assets:** {params['assets']}")

## from test_frontend_portfolio_mean_reversion.py 
# payload = { #what is needed to pass into strategies 
#     "tickers": params['assets'],
#     "start_date": params['start_date'].isoformat(),
#     "end_date": params['end_date'].isoformat(),
#     "initial_capital": float(10000),
#     "strategy_name": params['strategy'],
#     "strategy_params": {
#         "bb_window": int(params['params']['bb_window']),
#         "bb_std": float(2.0),
#         "rsi_window": int(14),
#         "rsi_entry": float(params['params']['rsi_low']), 
#         "rsi_exit": float(params['params']['rsi_high']),
#     },
# }
# tickers = params['assets']
# st.subheader("Request Body")
# st.json(payload)
    # Call backend
    with st.spinner("Running backtest..."):
        try:
            response = requests.post(
                "http://127.0.0.1:8000/backtest/run",
                json=payload,
                timeout=30
            )

            if response.status_code != 200:
                st.error(f"API Error: {response.status_code}")
                st.write(response.text)
                st.stop()

            data = response.json()

        except Exception as e:
            st.error(f"Request failed: {e}")
            st.stop()

    # Transform backend → frontend format

    df = pd.DataFrame(data["signal_rows"])
    df["Date"] = pd.to_datetime(df["Date"])
    df.set_index("Date", inplace=True)

    results = {
        "data": df,
        "equity_curve": df["strategy_eq"],
        "trades": data.get("trades", [])
    }

    # -------------------------
    # Render charts
    # -------------------------
    render_charts(results)

# -------------------------
# Run Pipeline
# -------------------------
# if st.button("Run Backtest"):
#     if not tickers:
#         st.warning("Please select at least one ticker.")
#     else:
#         response = requests.post(
#             "http://127.0.0.1:8000/backtest/run-portfolio",
#             json=payload
#         )

#         if response.status_code != 200:
#             st.error(f"API error: {response.status_code}")
#             try:
#                 st.json(response.json())
#             except Exception:
#                 st.write(response.text)
#         else:
#             data = response.json()
#             render_metrics(data)
#             render_charts(data)