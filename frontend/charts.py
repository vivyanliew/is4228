import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def render_charts_mean_reversion(results):
    data = results
    df = pd.DataFrame(data["portfolio_signal_rows"])
    df["Date"] = pd.to_datetime(df["Date"])

    st.subheader("Portfolio Equity Curve")
    fig_eq = go.Figure()
    fig_eq.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["portfolio_strategy_eq"],
            name="Portfolio Strategy Equity"
        )
    )
    fig_eq.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["portfolio_buyhold_eq"],
            name="Portfolio Buy & Hold"
        )
    )
    st.plotly_chart(fig_eq, use_container_width=True)

    st.subheader("Portfolio Signal Rows")
    st.dataframe(df.tail(50), use_container_width=True)


def render_charts_trend(results):
    
    data = results

    st.subheader("Multi-Ticker Equity Comparison")
    fig_multi_eq = go.Figure()
    for ticker_name in data["tickers"]:
        ticker_df = pd.DataFrame(data["per_ticker_signal_rows"][ticker_name])
        ticker_df["Date"] = pd.to_datetime(ticker_df["Date"])
        fig_multi_eq.add_trace(
            go.Scatter(
                x=ticker_df["Date"],
                y=ticker_df["strategy_eq"],
                name=f"{ticker_name} Strategy",
            )
        )
        fig_multi_eq.add_trace(
            go.Scatter(
                x=ticker_df["Date"],
                y=ticker_df["buyhold_eq"],
                name=f"{ticker_name} Buy & Hold",
                line={"dash": "dot"},
            )
        )
    st.plotly_chart(fig_multi_eq, use_container_width=True)

    st.subheader("Inspect Individual Ticker")
    selected_ticker = st.selectbox("Ticker", data["tickers"])
    ticker_df = pd.DataFrame(data["per_ticker_signal_rows"][selected_ticker])
    ticker_df["Date"] = pd.to_datetime(ticker_df["Date"])

    st.subheader(f"{selected_ticker} Price + EMA Cross Signals")
    fig_price = go.Figure()
    fig_price.add_trace(go.Scatter(x=ticker_df["Date"], y=ticker_df["Close"], name="Close"))
    fig_price.add_trace(go.Scatter(x=ticker_df["Date"], y=ticker_df["ema_fast"], name="Fast EMA"))
    fig_price.add_trace(go.Scatter(x=ticker_df["Date"], y=ticker_df["ema_slow"], name="Slow EMA"))
    fig_price.add_trace(
        go.Scatter(x=ticker_df["Date"], y=ticker_df["buy_marker"], mode="markers", name="Buy")
    )
    fig_price.add_trace(
        go.Scatter(x=ticker_df["Date"], y=ticker_df["sell_marker"], mode="markers", name="Sell")
    )
    st.plotly_chart(fig_price, use_container_width=True)

    st.subheader(f"{selected_ticker} ADX")
    fig_adx = go.Figure()
    fig_adx.add_trace(go.Scatter(x=ticker_df["Date"], y=ticker_df["adx"], name="ADX"))
    fig_adx.add_trace(
        go.Scatter(
            x=ticker_df["Date"],
            y=ticker_df["adx_threshold"],
            name="ADX Threshold",
            line={"dash": "dash"},
        )
    )
    st.plotly_chart(fig_adx, use_container_width=True)

    st.subheader(f"{selected_ticker} Equity Curve")
    fig_ticker_eq = go.Figure()
    fig_ticker_eq.add_trace(
        go.Scatter(x=ticker_df["Date"], y=ticker_df["strategy_eq"], name="Strategy Equity")
    )
    fig_ticker_eq.add_trace(
        go.Scatter(x=ticker_df["Date"], y=ticker_df["buyhold_eq"], name="Buy & Hold")
    )
    st.plotly_chart(fig_ticker_eq, use_container_width=True)

    return 


def render_charts_breakout(results):
    
    data = results

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
