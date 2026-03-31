import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Multi-Ticker MACD Viewer", layout="wide")
st.title("Equal-Weight Multi-Ticker MACD Backtest")

st.subheader("Inputs")

tickers = st.multiselect(
    "Tickers",
    ["AAPL", "MSFT", "NVDA", "TSLA", "SPY", "QQQ", "BTC-USD", "ETH-USD"],
    default=["AAPL", "MSFT", "NVDA"]
)

start_date = st.text_input("Start Date", value="2015-01-01")
end_date = st.text_input("End Date", value="2025-01-01")
initial_capital = st.number_input("Initial Capital", value=10000.0)

col1, col2, col3 = st.columns(3)
with col1:
    macd_fast = st.number_input("MACD Fast", value=12)
with col2:
    macd_slow = st.number_input("MACD Slow", value=26)
with col3:
    macd_signal = st.number_input("MACD Signal", value=9)

col4, col5, col6 = st.columns(3)
with col4:
    bb_window = st.number_input("BB Window", value=20)
with col5:
    bb_std = st.number_input("BB Std", value=2.0)
with col6:
    squeeze_quantile_window = st.number_input("Squeeze Quantile Window", value=20)

squeeze_threshold_quantile = st.number_input("Squeeze Threshold Quantile", value=0.2)

payload = {
    "tickers": tickers,
    "start_date": start_date,
    "end_date": end_date,
    "initial_capital": float(initial_capital),
    "strategy_name": "macd",
    "strategy_params": {
        "macd_fast": int(macd_fast),
        "macd_slow": int(macd_slow),
        "macd_signal": int(macd_signal),
        "bb_window": int(bb_window),
        "bb_std": float(bb_std),
        "squeeze_quantile_window": int(squeeze_quantile_window),
        "squeeze_threshold_quantile": float(squeeze_threshold_quantile),
    },
}

st.subheader("Request Body")
st.json(payload)

if st.button("Run Multi-Ticker MACD Backtest"):
    if not tickers:
        st.warning("Please select at least one ticker.")
    else:
        response = requests.post(
            "http://127.0.0.1:8000/backtest/run-macd-multi",
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

            st.subheader("Metrics")
            st.json(data["metrics"])

            st.subheader("Trades")
            if data["trades"]:
                trades_df = pd.DataFrame(data["trades"])
                st.dataframe(trades_df, use_container_width=True)
            else:
                st.info("No trades executed")

            df = pd.DataFrame(data["signal_rows"])
            df["Date"] = pd.to_datetime(df["Date"])

            st.subheader("Equity Curve")
            fig_eq = go.Figure()
            fig_eq.add_trace(
                go.Scatter(
                    x=df["Date"],
                    y=df["strategy_eq"],
                    name="Strategy Equity"
                )
            )
            fig_eq.add_trace(
                go.Scatter(
                    x=df["Date"],
                    y=df["buyhold_eq"],
                    name="Buy & Hold (Equal Weight)"
                )
            )
            st.plotly_chart(fig_eq, use_container_width=True)

            st.subheader("Signal Rows (Last 50)")
            st.dataframe(df.tail(50), use_container_width=True)
