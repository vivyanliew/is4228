import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(page_title="Trend Follower Backtest Viewer", layout="wide")
st.title("Trend Follower Backtest Viewer")

st.subheader("Inputs")

ticker = st.text_input("Ticker", value="AAPL")
start_date = st.text_input("Start Date", value="2015-01-01")
end_date = st.text_input("End Date", value="2025-01-01")
initial_capital = st.number_input("Initial Capital", value=10000.0)

col1, col2 = st.columns(2)
with col1:
    ema_fast = st.number_input("Fast EMA", value=20)
with col2:
    ema_slow = st.number_input("Slow EMA", value=50)

col3, col4 = st.columns(2)
with col3:
    adx_window = st.number_input("ADX Window", value=14)
with col4:
    adx_threshold = st.number_input("ADX Threshold", value=25.0)

payload = {
    "ticker": ticker,
    "start_date": start_date,
    "end_date": end_date,
    "initial_capital": float(initial_capital),
    "strategy_name": "trend_follower",
    "strategy_params": {
        "ema_fast": int(ema_fast),
        "ema_slow": int(ema_slow),
        "adx_window": int(adx_window),
        "adx_threshold": float(adx_threshold),
    },
}

st.subheader("Request Body")
st.json(payload)

if st.button("Run Backtest"):
    response = requests.post(
        "http://127.0.0.1:8000/backtest/run",
        json=payload,
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

        st.subheader("Price + EMA Cross Signals")
        fig_price = go.Figure()
        fig_price.add_trace(go.Scatter(x=df["Date"], y=df["Close"], name="Close"))
        fig_price.add_trace(go.Scatter(x=df["Date"], y=df["ema_fast"], name="Fast EMA"))
        fig_price.add_trace(go.Scatter(x=df["Date"], y=df["ema_slow"], name="Slow EMA"))
        fig_price.add_trace(
            go.Scatter(x=df["Date"], y=df["buy_marker"], mode="markers", name="Buy")
        )
        fig_price.add_trace(
            go.Scatter(x=df["Date"], y=df["sell_marker"], mode="markers", name="Sell")
        )
        st.plotly_chart(fig_price, use_container_width=True)

        st.subheader("ADX")
        fig_adx = go.Figure()
        fig_adx.add_trace(go.Scatter(x=df["Date"], y=df["adx"], name="ADX"))
        fig_adx.add_trace(
            go.Scatter(
                x=df["Date"],
                y=df["adx_threshold"],
                name="ADX Threshold",
                line={"dash": "dash"},
            )
        )
        st.plotly_chart(fig_adx, use_container_width=True)

        st.subheader("Equity Curve")
        fig_eq = go.Figure()
        fig_eq.add_trace(
            go.Scatter(x=df["Date"], y=df["strategy_eq"], name="Strategy Equity")
        )
        fig_eq.add_trace(go.Scatter(x=df["Date"], y=df["buyhold_eq"], name="Buy & Hold"))
        st.plotly_chart(fig_eq, use_container_width=True)

