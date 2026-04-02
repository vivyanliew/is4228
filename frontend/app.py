import streamlit as st
import requests

from api import build_payload
from sidebar import render_sidebar
from charts import render_charts_mean_reversion, render_charts_trend, render_charts_breakout
from metrics import render_metrics_mean_reversion, render_metrics_trend, render_metrics_breakout

st.set_page_config(page_title="Strategy Backtester", layout="wide")

st.title("Strategy Research & Backtesting Tool")

if "submitted_params" not in st.session_state:
    st.session_state["submitted_params"] = None

STRATEGY_REGISTRY = {
    "mean_reversion": {
        "endpoint": "http://127.0.0.1:8000/backtest/run-portfolio"
    },
    "trend": {
        "endpoint": "http://127.0.0.1:8000/backtest/run-portfolio" ##change this accordingly
    },
    "macd": {
        "endpoint": "http://127.0.0.1:8000/backtest/run-macd-multi"
    },
}

# -------------------------
# Sidebar Inputs
# -------------------------
params = render_sidebar()

if params["run"]:
    st.session_state["submitted_params"] = params

active_params = st.session_state["submitted_params"]

if active_params is None:
    st.info("Configure your strategy in the sidebar and click 'Run Backtest'.")
else:
    st.success("Backtest configuration captured.")

    payload = build_payload(active_params)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Configuration")
        st.json(payload)

    with col2:
        st.subheader("Summary")
        st.write(f"**Tier:** {active_params['tier']}")
        st.write(f"**Strategy:** {active_params['strategy']}")
        st.write(f"**Assets:** {active_params['assets']}")

    strategy_name = active_params["strategy"]
    strategy = STRATEGY_REGISTRY[strategy_name]
    tickers = active_params["assets"]

    if st.button("Run Portfolio Backtest"):
        if not tickers:
            st.warning("Please select at least one ticker.")
        else:
            try:
                with st.spinner("Running portfolio backtest..."):
                    response = requests.post(
                        strategy["endpoint"],
                        json=payload,
                        timeout=60,
                    )

                if response.status_code != 200:
                    st.error(f"API error: {response.status_code}")
                    try:
                        st.json(response.json())
                    except Exception:
                        st.write(response.text)
                else:
                    data = response.json()

                    if strategy_name == "mean_reversion":
                        render_metrics_mean_reversion(data)
                        render_charts_mean_reversion(data)
                    elif strategy_name == "trend":
                        render_metrics_trend(data)
                        render_charts_trend(data)
                    else:
                        render_metrics_breakout(data)
                        render_charts_breakout(data)
            except requests.RequestException as exc:
                st.error(
                    "Could not reach the backend API at http://127.0.0.1:8000. "
                    f"Details: {exc}"
                )
