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
