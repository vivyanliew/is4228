import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Backtest Debug Viewer", layout="wide")
st.title("Strategy Backtest Debug Viewer")

st.subheader("Inputs")

ticker = st.text_input("Ticker", value="AAPL")
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

col4, col5 = st.columns(2)
with col4:
    bb_window = st.number_input("BB Window", value=20)
with col5:
    bb_std = st.number_input("BB Std", value=2.0)

col6, col7 = st.columns(2)
with col6:
    squeeze_quantile_window = st.number_input("Squeeze Quantile Window", value=20)
with col7:
    squeeze_threshold_quantile = st.number_input("Squeeze Threshold Quantile", value=0.2)

payload = {
    "ticker": ticker,
    "start_date": start_date,
    "end_date": end_date,
    "initial_capital": initial_capital,
    "macd_fast": int(macd_fast),
    "macd_slow": int(macd_slow),
    "macd_signal": int(macd_signal),
    "bb_window": int(bb_window),
    "bb_std": float(bb_std),
    "squeeze_quantile_window": int(squeeze_quantile_window),
    "squeeze_threshold_quantile": float(squeeze_threshold_quantile),
}

st.subheader("Request Body")
st.json(payload)

if st.button("Run Backtest"):
    response = requests.post(
        "http://127.0.0.1:8000/backtest/macd-breakout",
        json=payload
    )

    if response.status_code != 200:
        st.error(f"API error: {response.status_code}")
        st.json(response.json())
    else:
        data = response.json()

        st.subheader("Metrics")
        st.json(data["metrics"])

        if data["trades"]:
            st.subheader("Trades")
            trades_df = pd.DataFrame(data["trades"])
            st.dataframe(trades_df, use_container_width=True)
        else:
            st.info("No trades generated.")

        df = pd.DataFrame(data["signal_rows"])
        df["Date"] = pd.to_datetime(df["Date"])

        st.subheader("Price + Buy/Sell Signals")
        fig_price = go.Figure()
        fig_price.add_trace(go.Scatter(x=df["Date"], y=df["Close"], name="Close"))
        fig_price.add_trace(go.Scatter(x=df["Date"], y=df["buy_marker"], mode="markers", name="Buy"))
        fig_price.add_trace(go.Scatter(x=df["Date"], y=df["sell_marker"], mode="markers", name="Sell"))
        st.plotly_chart(fig_price, use_container_width=True)

        st.subheader("Equity Curve")
        fig_eq = go.Figure()
        fig_eq.add_trace(go.Scatter(x=df["Date"], y=df["strategy_eq"], name="Strategy Equity"))
        fig_eq.add_trace(go.Scatter(x=df["Date"], y=df["buyhold_eq"], name="Buy & Hold"))
        st.plotly_chart(fig_eq, use_container_width=True)