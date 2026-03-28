import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Mean Reversion Backtest Viewer", layout="wide")
st.title("Mean Reversion Backtest Viewer")

st.subheader("Inputs")

ticker = st.text_input("Ticker", value="AAPL")
start_date = st.text_input("Start Date", value="2015-01-01")
end_date = st.text_input("End Date", value="2025-01-01")
initial_capital = st.number_input("Initial Capital", value=10000.0)

col1, col2 = st.columns(2)
with col1:
    bb_window = st.number_input("BB Window", value=20)
with col2:
    bb_std = st.number_input("BB Std", value=2.0)

col3, col4, col5 = st.columns(3)
with col3:
    rsi_window = st.number_input("RSI Window", value=14)
with col4:
    rsi_entry = st.number_input("RSI Entry Threshold", value=30)
with col5:
    rsi_exit = st.number_input("RSI Exit Threshold", value=70)

payload = {
    "ticker": ticker,
    "start_date": start_date,
    "end_date": end_date,
    "initial_capital": float(initial_capital),
    "strategy_name": "mean_reversion",
    "strategy_params": {
        "bb_window": int(bb_window),
        "bb_std": float(bb_std),
        "rsi_window": int(rsi_window),
        "rsi_entry": float(rsi_entry),
        "rsi_exit": float(rsi_exit),
    },
}

st.subheader("Request Body")
st.json(payload)

if st.button("Run Backtest"):
    response = requests.post(
        "http://127.0.0.1:8000/backtest/run",
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
        fig_price.add_trace(
            go.Scatter(
                x=df["Date"],
                y=df["buy_marker"],
                mode="markers",
                name="Buy"
            )
        )
        fig_price.add_trace(
            go.Scatter(
                x=df["Date"],
                y=df["sell_marker"],
                mode="markers",
                name="Sell"
            )
        )
        st.plotly_chart(fig_price, use_container_width=True)

        st.subheader("Equity Curve")
        fig_eq = go.Figure()
        fig_eq.add_trace(go.Scatter(x=df["Date"], y=df["strategy_eq"], name="Strategy Equity"))
        fig_eq.add_trace(go.Scatter(x=df["Date"], y=df["buyhold_eq"], name="Buy & Hold"))
        st.plotly_chart(fig_eq, use_container_width=True)

        st.subheader("Signal Rows")
        st.dataframe(df.tail(50), use_container_width=True)