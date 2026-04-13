import pandas as pd
import requests
import streamlit as st

from api import (
    AGENT_MARKET_CONTEXT_URL,
    MARKET_INTEL_URL,
    STRATEGY_GENERATION_URL,
    build_payload,
    get_backtest_endpoint,
)
from charts import render_charts_breakout, render_charts_mean_reversion, render_charts_trend
from metrics import render_metrics_breakout, render_metrics_mean_reversion, render_metrics_trend
from sidebar import ASSETS, STRATEGIES

st.set_page_config(page_title="Strategy Lab", layout="wide")

TIER_RANK = {
    "Free": 1,
    "Pro": 2,
    "Advanced": 3,
}

TIER_COPY = {
    "Free": "Backtester access with the three core strategies and optional portfolio runs.",
    "Pro": "Adds Market Intelligence on top of the backtester.",
    "Advanced": "Unlocks the full workflow, including Strategy Generation.",
}

if "backtest_data" not in st.session_state:
    st.session_state["backtest_data"] = None
if "backtest_strategy" not in st.session_state:
    st.session_state["backtest_strategy"] = None
if "market_intel_result" not in st.session_state:
    st.session_state["market_intel_result"] = None
if "strategy_generation_result" not in st.session_state:
    st.session_state["strategy_generation_result"] = None
if "strategy_generation_market_context" not in st.session_state:
    st.session_state["strategy_generation_market_context"] = None
if "strategy_generation_show_raw" not in st.session_state:
    st.session_state["strategy_generation_show_raw"] = False
if "selected_tier" not in st.session_state:
    st.session_state["selected_tier"] = "Free"
if "backtest_mode" not in st.session_state:
    st.session_state["backtest_mode"] = "Single Asset"
if "backtest_portfolio_assets" not in st.session_state:
    st.session_state["backtest_portfolio_assets"] = ["AAPL", "MSFT"]
if "backtest_single_asset_value" not in st.session_state:
    st.session_state["backtest_single_asset_value"] = ASSETS[0]


def tier_enabled(active_tier: str, required_tier: str) -> bool:
    return TIER_RANK[active_tier] >= TIER_RANK[required_tier]


def render_header():
    left_col, right_col = st.columns([4, 2])

    with left_col:
        st.title("Strategy Lab")
        st.caption("Market intelligence, backtesting, and AI-assisted strategy generation in one workspace.")

    with right_col:
        st.markdown(
            """
            <div style="display:flex; justify-content:flex-end; align-items:center; gap:12px; margin-top:8px;">
                <div style="text-align:right;">
                    <div style="font-size:0.8rem; color:#6b7280;">Profile</div>
                    <div style="font-weight:600;">MVP User</div>
                </div>
                <div style="
                    width:42px;
                    height:42px;
                    border-radius:999px;
                    background:linear-gradient(135deg, #1d4ed8, #0f766e);
                    color:white;
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    font-weight:700;
                    font-size:0.95rem;
                ">MU</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tier_options = ["Free", "Pro", "Advanced"]
        try:
            selected_tier = st.segmented_control(
                "Tier",
                options=tier_options,
                default=st.session_state["selected_tier"],
                key="tier_selector",
                help="Toggle the MVP tiers to preview what each user level can access.",
            )
        except Exception:
            selected_tier = st.radio(
                "Tier",
                options=tier_options,
                index=tier_options.index(st.session_state["selected_tier"]),
                key="tier_selector_fallback",
                horizontal=True,
                help="Toggle the MVP tiers to preview what each user level can access.",
            )
        st.session_state["selected_tier"] = selected_tier
        st.caption(TIER_COPY[st.session_state["selected_tier"]])


def render_market_intelligence_tab(active_tier: str):
    st.subheader("Market Intelligence")
    st.caption("Fetch a quick company snapshot, recent news, and an AI summary.")

    if not tier_enabled(active_tier, "Pro"):
        st.info("Available from the Pro tier onward. Switch the tier at the top right to unlock this tab.")
        return

    with st.form("market_intel_form"):
        col1, col2 = st.columns([2, 1])
        with col1:
            ticker = st.selectbox("Ticker", options=ASSETS, index=0)
        with col2:
            show_raw = st.toggle("Show Raw API Response", value=False)
        submitted = st.form_submit_button("Fetch Market Intelligence", use_container_width=True)

    if submitted:
        try:
            with st.spinner(f"Fetching market intelligence for {ticker}..."):
                response = requests.get(f"{MARKET_INTEL_URL}/{ticker}", timeout=30)

            if response.status_code != 200:
                st.session_state["market_intel_result"] = {
                    "request_error": f"API error {response.status_code}",
                    "response_body": response.text,
                }
            else:
                st.session_state["market_intel_result"] = response.json()
                st.session_state["market_intel_show_raw"] = show_raw
        except Exception as exc:
            st.session_state["market_intel_result"] = {
                "request_error": "Backend connection failed",
                "response_body": str(exc),
            }
            st.session_state["market_intel_show_raw"] = show_raw

    data = st.session_state["market_intel_result"]
    show_raw = st.session_state.get("market_intel_show_raw", False)

    if not data:
        st.info("Choose a ticker and fetch market intelligence.")
        return

    if "request_error" in data:
        st.error(data["request_error"])
        st.code(data["response_body"])
        return

    if "error" in data:
        st.error(data["error"])
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Ticker", data["ticker"])
    with col2:
        st.metric("Revenue", f"${data['revenue']:,.0f}")
    with col3:
        st.metric("EPS", f"{data['eps']:.2f}")

    sentiment = data.get("sentiment", "Neutral")
    if sentiment == "Positive":
        st.success(f"Sentiment: {sentiment}")
    elif sentiment == "Negative":
        st.error(f"Sentiment: {sentiment}")
    else:
        st.info(f"Sentiment: {sentiment}")

    st.subheader("AI Summary")
    st.write(data.get("llm_summary", "No AI summary available."))

    st.subheader("Recent News")
    for article in data.get("news", []):
        with st.container(border=True):
            st.markdown(f"**{article.get('title', 'Untitled article')}**")
            if article.get("url"):
                st.markdown(f"[Open article]({article['url']})")

    if show_raw:
        st.subheader("Raw API Response")
        st.json(data)


def render_backtester_tab(active_tier: str):
    st.subheader("Backtester")
    st.caption("Configure a strategy and run it against historical data.")

    strategy_options = list(STRATEGIES.items())
    control_box = st.container(border=True)
    with control_box:
        col1, col2, col3 = st.columns(3)
        with col1:
            strategy_label = st.selectbox(
                "Strategy",
                options=[label for label, _ in strategy_options],
            )
        with col2:
            mode = st.radio(
                "Mode",
                options=["Single Asset", "Portfolio"],
                horizontal=True,
                index=["Single Asset", "Portfolio"].index(st.session_state["backtest_mode"]),
                key="backtest_mode_widget",
            )
        with col3:
            initial_capital = st.number_input("Initial Capital", min_value=1000, value=10000, step=1000)

        st.session_state["backtest_mode"] = mode

        if mode == "Single Asset":
            single_asset = st.selectbox(
                "Ticker",
                options=ASSETS,
                index=ASSETS.index(st.session_state["backtest_single_asset_value"]),
                key="backtest_single_asset",
            )
            st.session_state["backtest_single_asset_value"] = single_asset
            assets = [single_asset]
        else:
            assets = st.multiselect(
                "Tickers",
                options=ASSETS,
                default=st.session_state["backtest_portfolio_assets"],
                key="backtest_portfolio_assets_widget",
            )
            st.session_state["backtest_portfolio_assets"] = assets
            st.caption(f"{len(assets)} ticker(s) selected")

        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("Start Date", value=pd.to_datetime("2025-01-01"), key="backtest_start")
        with date_col2:
            end_date = st.date_input("End Date", value=pd.to_datetime("2025-12-31"), key="backtest_end")

        strategy = STRATEGIES[strategy_label]
        params = {}
        if strategy == "mean_reversion":
            p1, p2, p3 = st.columns(3)
            with p1:
                params["rsi_low"] = st.slider("RSI Oversold", 10, 50, 30)
            with p2:
                params["rsi_high"] = st.slider("RSI Overbought", 50, 90, 70)
            with p3:
                params["bb_window"] = st.slider("Bollinger Window", 10, 50, 20)
        elif strategy == "trend_follower":
            p1, p2, p3 = st.columns(3)
            with p1:
                params["ema_short"] = st.slider("EMA Short", 5, 50, 20)
            with p2:
                params["ema_long"] = st.slider("EMA Long", 20, 200, 50)
            with p3:
                params["adx_threshold"] = st.slider("ADX Threshold", 10, 50, 25)
        else:
            p1, p2 = st.columns(2)
            with p1:
                params["macd_fast"] = st.slider("MACD Fast", 5, 20, 12)
            with p2:
                params["macd_slow"] = st.slider("MACD Slow", 20, 50, 26)

        params["initial_capital"] = initial_capital
        submitted = st.button("Run Backtest", use_container_width=True, key="run_backtest_button")

    if submitted:
        if not assets:
            st.warning("Please select at least one ticker.")
        else:
            config = {
                "assets": assets,
                "start_date": start_date,
                "end_date": end_date,
                "strategy": strategy,
                "params": params,
            }
            payload = build_payload(config)
            endpoint = get_backtest_endpoint(strategy, assets)
            try:
                with st.spinner("Running backtest..."):
                    response = requests.post(endpoint, json=payload, timeout=60)
                if response.status_code != 200:
                    st.error(f"API error: {response.status_code}")
                    try:
                        st.json(response.json())
                    except Exception:
                        st.write(response.text)
                else:
                    st.session_state["backtest_data"] = response.json()
                    st.session_state["backtest_strategy"] = strategy
            except requests.RequestException as exc:
                st.error(f"Could not reach backend API. Details: {exc}")

    st.caption(f"Current tier: `{active_tier}`. Free users can use all three built-in strategies and optional portfolio backtests.")

    data = st.session_state["backtest_data"]
    strategy = st.session_state["backtest_strategy"]
    if not data or not strategy:
        st.info("Run a backtest to view results here.")
        return

    st.divider()
    if "portfolio_metrics" not in data:
        st.subheader("Metrics")
        st.json(data.get("metrics", {}))
        signal_rows = data.get("signal_rows", [])
        if signal_rows:
            df = pd.DataFrame(signal_rows)
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"])
                st.line_chart(df.set_index("Date")[["strategy_eq", "buyhold_eq"]])
            st.subheader("Signal Rows")
            st.dataframe(df.tail(50), use_container_width=True, hide_index=True)
        return

    if strategy == "mean_reversion":
        render_metrics_mean_reversion(data)
        render_charts_mean_reversion(data)
    elif strategy == "trend_follower":
        render_metrics_trend(data)
        render_charts_trend(data)
    else:
        render_metrics_breakout(data)
        render_charts_breakout(data)


def render_strategy_generation_tab(active_tier: str):
    st.subheader("Strategy Generation")
    st.caption("Market context is analyzed first, then strategy ideas are generated from that context.")

    if not tier_enabled(active_tier, "Advanced"):
        st.info("Available only on the Advanced tier. Switch the tier at the top right to access strategy generation.")
        return

    control_box = st.container(border=True)
    with control_box:
        row1, row2 = st.columns([2, 1])
        with row1:
            ticker = st.selectbox("Ticker", options=ASSETS, index=0, key="gen_ticker")
        with row2:
            max_candidates = st.slider("Max Candidates", min_value=1, max_value=5, value=3)

        row3, row4 = st.columns(2)
        with row3:
            start_date = st.date_input("Start Date", value=pd.to_datetime("2022-01-01"), key="gen_start")
        with row4:
            end_date = st.date_input("End Date", value=pd.to_datetime("2024-12-31"), key="gen_end")

        row8, row9 = st.columns([1, 1])
        with row8:
            use_llm = st.toggle("Use Cohere if available", value=True)
        with row9:
            show_raw = st.toggle("Show Raw API Response", value=st.session_state["strategy_generation_show_raw"])

        st.session_state["strategy_generation_show_raw"] = show_raw
        submitted = st.button("Generate Strategies", use_container_width=True, key="generate_strategies_button")

    if submitted:
        try:
            market_context_payload = {
                "ticker": ticker,
                "start_date": str(start_date),
                "end_date": str(end_date),
            }
            with st.spinner("Analyzing market context..."):
                context_response = requests.post(
                    AGENT_MARKET_CONTEXT_URL,
                    json=market_context_payload,
                    timeout=60,
                )
            if context_response.status_code != 200:
                st.error(f"Market context API error: {context_response.status_code}")
                try:
                    st.json(context_response.json())
                except Exception:
                    st.write(context_response.text)
                return

            market_context = context_response.json()
            st.session_state["strategy_generation_market_context"] = market_context

            payload = {
                "ticker": ticker,
                "start_date": str(start_date),
                "end_date": str(end_date),
                "market_context": market_context,
                "max_candidates": max_candidates,
                "use_llm": use_llm,
                "allow_experimental": True,
            }
            with st.spinner("Generating strategy candidates..."):
                response = requests.post(STRATEGY_GENERATION_URL, json=payload, timeout=60)
            if response.status_code != 200:
                st.error(f"API error: {response.status_code}")
                try:
                    st.json(response.json())
                except Exception:
                    st.write(response.text)
            else:
                st.session_state["strategy_generation_result"] = response.json()
        except requests.RequestException as exc:
            st.error(f"Could not reach backend API. Details: {exc}")

    data = st.session_state["strategy_generation_result"]
    if not data:
        st.info("Generate strategies to view candidates here.")
        return

    st.divider()
    st.subheader("Research Setup")
    meta1, meta2, meta3, meta4 = st.columns(4)
    with meta1:
        st.metric("Ticker", data["ticker"])
    with meta2:
        st.metric("Start", data["start_date"])
    with meta3:
        st.metric("End", data["end_date"])
    with meta4:
        st.metric("Candidates", len(data.get("strategies", [])))

    context = st.session_state.get("strategy_generation_market_context") or data.get("market_context", {})
    if context:
        st.subheader("Market Context")
        st.caption("This market-context analysis is used to guide the generated strategy ideas.")

        context_col1, context_col2, context_col3 = st.columns(3)
        with context_col1:
            st.metric("Market Regime", str(context.get("regime", "n/a")).replace("_", " ").title())
            st.metric("Strategy Bias", str(context.get("strategy_bias", "n/a")).replace("_", " ").title())
        with context_col2:
            st.metric("Trend Direction", str(context.get("trend_direction", "n/a")).replace("_", " ").title())
            st.metric("30D Realized Vol", context.get("realized_vol_30d", "n/a"))
        with context_col3:
            st.metric("SPY Correlation", context.get("correlation_to_spy", "n/a"))
            st.metric("SMA 200 Slope", context.get("sma_200_slope", "n/a"))

        reasoning = context.get("reasoning", "")
        if reasoning:
            with st.container(border=True):
                st.markdown("**Why this market context was identified**")
                st.write(reasoning)

    st.subheader("Generated Candidates")
    for index, strategy in enumerate(data.get("strategies", []), start=1):
        title = strategy["strategy_name"].replace("_", " ").title()
        badge = strategy.get("source", "unknown")
        with st.expander(f"{index}. {title} [{badge}]", expanded=index == 1):
            top_left, top_right, top_far = st.columns([2, 1, 1])
            with top_left:
                st.write(strategy.get("description", ""))
            with top_right:
                st.caption(f"Source: {badge}")
            with top_far:
                if strategy.get("backtestable", False):
                    st.success("Backtestable Now")
                else:
                    st.warning("Experimental")
            if strategy.get("rationale"):
                st.caption(strategy["rationale"])

            info1, info2 = st.columns(2)
            with info1:
                st.metric("Confidence", f"{float(strategy.get('confidence', 0)):.2f}")
            with info2:
                research_basis = strategy.get("research_basis", [])
                st.caption("Research Basis")
                if research_basis:
                    st.write(", ".join(research_basis))
                else:
                    st.write("None attached")

            params_df = pd.DataFrame(
                [
                    {"Parameter": key, "Value": value}
                    for key, value in strategy.get("strategy_params", {}).items()
                ]
            )
            if not params_df.empty:
                st.dataframe(params_df, use_container_width=True, hide_index=True)

            if strategy.get("metadata"):
                metadata_items = [
                    f"`{key}`: {value}"
                    for key, value in strategy["metadata"].items()
                ]
                if metadata_items:
                    st.markdown(" | ".join(metadata_items))

            if strategy.get("implementation_hint"):
                st.info(strategy["implementation_hint"])

            if strategy.get("generated_code"):
                st.code(strategy["generated_code"], language="python")

    if st.session_state["strategy_generation_show_raw"]:
        st.subheader("Raw API Response")
        st.json(data)


render_header()
active_tier = st.session_state["selected_tier"]

backtest_tab, market_tab, strategy_tab = st.tabs(
    ["Backtester", "Market Intelligence", "Strategy Generation"]
)

with backtest_tab:
    render_backtester_tab(active_tier)

with market_tab:
    render_market_intelligence_tab(active_tier)

with strategy_tab:
    render_strategy_generation_tab(active_tier)
