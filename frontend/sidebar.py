import streamlit as st
import pandas as pd

# CONSTANTS
ASSETS = [
    "AAPL", "NVDA", "MSFT", "GOOGL", "TSLA",
    "AMD", "NFLX", "META", "AMZN", "WMT",
    "COST", "SBUX", "JPM", "GS", "BRK-B",
    "V", "UNH", "LLY", "XOM", "CVX", "BTC-USD"
]

STRATEGIES = {
    "Mean Reversion (RSI + Bollinger)": "mean_reversion",
    "Trend Follower (EMA + ADX)": "trend",
    "Volatility Breakout (MACD + BB Width)": "breakout"
}

TIERS = {
    "Free (Learning)": "free",
    "Pro (Strategy Builder)": "pro",
    "Advanced (Custom Backtest)": "advanced"
}

# MAIN SIDEBAR FUNCTION

def render_sidebar():
    st.sidebar.title(" Strategy Lab")

    # Tier Selection
    st.sidebar.markdown("### Select Tier")
    tier_label = st.sidebar.radio(
        "Choose your experience level:",
        list(TIERS.keys())
    )
    tier = TIERS[tier_label]

    st.sidebar.divider()

    # Asset Selection
    st.sidebar.markdown("### 📈 Asset Selection")

    if tier == "free":
        asset = st.sidebar.selectbox("Select Asset", ASSETS)
        assets = [asset]
    else:
        assets = st.sidebar.multiselect(
            "Select Assets",
            ASSETS,
            default=["AAPL", "MSFT"]
        )

    # Date Range
    st.sidebar.markdown("### Date Range")

    start_date = st.sidebar.date_input(
        "Start Date",
        value=pd.to_datetime("2022-01-01")
    )

    end_date = st.sidebar.date_input(
        "End Date",
        value=pd.to_datetime("2025-12-31")  
    )

    st.sidebar.divider()

    # Strategy Selection
    st.sidebar.markdown("### Strategy")

    if tier == "free":
        strategy_label = st.sidebar.selectbox(
            "Choose Strategy",
            ["Mean Reversion (RSI + Bollinger)"]
        )
    else:
        strategy_label = st.sidebar.selectbox(
            "Choose Strategy",
            list(STRATEGIES.keys())
        )

    strategy = STRATEGIES[strategy_label]

    # Hyperparameters
    st.sidebar.markdown("### Parameters")

    params = {}

    # Strategy-specific controls
    if strategy == "mean_reversion":
        params["rsi_low"] = st.sidebar.slider("RSI Oversold", 10, 50, 30)
        params["rsi_high"] = st.sidebar.slider("RSI Overbought", 50, 90, 70)

        params["bb_window"] = st.sidebar.slider("Bollinger Window", 10, 50, 20)

    elif strategy == "trend":
        params["ema_short"] = st.sidebar.slider("EMA Short", 5, 50, 20)
        params["ema_long"] = st.sidebar.slider("EMA Long", 20, 200, 50)

        params["adx_threshold"] = st.sidebar.slider("ADX Threshold", 10, 50, 25)

    elif strategy == "breakout":
        params["macd_fast"] = st.sidebar.slider("MACD Fast", 5, 20, 12)
        params["macd_slow"] = st.sidebar.slider("MACD Slow", 20, 50, 26)

        params["bb_width"] = st.sidebar.slider("BB Squeeze Threshold", 1, 10, 5)

    st.sidebar.divider()

    # Advanced Controls (only highest tier)
    if tier == "advanced":
        st.sidebar.markdown("### Advanced Settings")

        params["initial_capital"] = st.sidebar.number_input(
            "Initial Capital ($)",
            min_value=1000,
            value=10000,
            step=1000
        )

        params["transaction_cost"] = st.sidebar.slider(
            "Transaction Cost (%)",
            0.0, 1.0, 0.1
        )

    # Run Button
    run = st.sidebar.button("Run Backtest")

    # RETURN CONFIG
    return {
        "tier": tier,
        "assets": assets,
        "start_date": start_date,
        "end_date": end_date,
        "strategy": strategy,
        "params": params,
        "run": run
    }