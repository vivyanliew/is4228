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
    "trend_follower": {
        "endpoint": "http://127.0.0.1:8000/backtest/run-portfolio" 
    },
    "macd": {
        "endpoint": "http://127.0.0.1:8000/backtest/run-macd-multi"
    },
}

# Sidebar Inputs
params = render_sidebar()

if params["run"]:
    st.session_state["submitted_params"] = params

    # Clear old results
    st.session_state.pop("backtest_data", None)
    st.session_state.pop("backtest_strategy", None)

    strategy_name = params["strategy"]
    strategy = STRATEGY_REGISTRY[strategy_name]
    tickers = params["assets"]
    tier = params["tier"]

    payload = build_payload(params)

    endpoint = strategy["endpoint"]

    if not tickers:
        st.warning("Please select at least one ticker.")
    else:
        try:
            with st.spinner("Running backtest..."):
                response = requests.post(
                    endpoint,
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
                st.session_state["backtest_data"] = data
                st.session_state["backtest_strategy"] = strategy_name
                st.success("Backtest completed!")

        except requests.RequestException as exc:
            st.error(
                "Could not reach backend API. "
                f"Details: {exc}"
            )
active_params = st.session_state["submitted_params"]

if active_params is None:
   st.info("Configure your strategy in the sidebar and click 'Run'.")

# Render results if available
if "backtest_data" in st.session_state:
    st.divider()
    st.header("Backtest Results")

    data = st.session_state["backtest_data"]
    strategy_name = st.session_state["backtest_strategy"]
    
    if strategy_name == "mean_reversion":
        render_metrics_mean_reversion(data)
        render_charts_mean_reversion(data)
    elif strategy_name == "trend_follower":
        render_metrics_trend(data)
        render_charts_trend(data)
    else:
        render_metrics_breakout(data)
        render_charts_breakout(data)
