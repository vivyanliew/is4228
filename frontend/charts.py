import markdown
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Styled color for benchmark metrics
BENCHMARK_STYLE = "color:#2E6B9E; font-weight:600;"  # steel blue
RISK_LOW_STYLE = "color:#2E8B57; font-weight:600;"   # sea green
RISK_MOD_STYLE = "color:#D4A017; font-weight:600;"   # goldenrod
RISK_HIGH_STYLE = "color:#C0392B; font-weight:600;"  # crimson


# ── shared portfolio section (identical for every strategy) ────────────────

def _render_portfolio_section(data):
    """Portfolio Equity Curve + Drawdown + metric cards."""
    df = pd.DataFrame(data["portfolio_signal_rows"])
    df["Date"] = pd.to_datetime(df["Date"])

    st.markdown("---")
    st.markdown(
        '<h3 style="text-decoration:underline;"><b>Portfolio Analysis</b></h3>',
        unsafe_allow_html=True,
    )

    # Equity curve
    st.subheader("Portfolio Equity Curve")
    fig_eq = go.Figure()
    fig_eq.add_trace(
        go.Scatter(x=df["Date"], y=df["portfolio_strategy_eq"], name="Portfolio Strategy Equity")
    )
    fig_eq.add_trace(
        go.Scatter(x=df["Date"], y=df["portfolio_buyhold_eq"], name="Portfolio Buy & Hold")
    )

    # SPY benchmark overlay
    bench = data.get("benchmark", {})
    if bench and "benchmark_equity_rows" in bench:
        bdf = pd.DataFrame(bench["benchmark_equity_rows"])
        bdf["Date"] = pd.to_datetime(bdf["Date"])
        fig_eq.add_trace(
            go.Scatter(
                x=bdf["Date"], y=bdf["bench_eq"],
                name=f'{bench.get("benchmark_ticker", "SPY")} Benchmark',
                line=dict(color="#FF8C00", dash="dot", width=2),
            )
        )

    st.plotly_chart(fig_eq, use_container_width=True)

    # Drawdown
    st.subheader("Portfolio Drawdown")
    port_peak = df["portfolio_strategy_eq"].cummax()
    df["portfolio_dd_pct"] = (df["portfolio_strategy_eq"] - port_peak) / port_peak * 100
    fig_dd = go.Figure()
    fig_dd.add_trace(
        go.Scatter(
            x=df["Date"], y=df["portfolio_dd_pct"],
            fill="tozeroy", name="Drawdown (%)",
            line=dict(color="red"),
        )
    )
    fig_dd.update_layout(yaxis_title="Drawdown (%)", yaxis_ticksuffix="%")
    st.plotly_chart(fig_dd, use_container_width=True)

    # Metric cards
    if "portfolio_metrics" in data:
        pm = data["portfolio_metrics"]
        m1, m2, m3 = st.columns(3)
        m1.metric("Cumulative Return", f"{pm.get('cumulative_return_pct', 0):.2f}%")
        m2.metric("Max Drawdown", f"{pm.get('max_drawdown_pct', 0):.2f}%")
        m3.metric("Sharpe Ratio", f"{pm.get('sharpe_ratio', 0):.4f}")

    # Benchmark-relative metrics
    _render_benchmark_metrics(data)


def _render_benchmark_metrics(data):
    """Render benchmark comparison metrics in styled blue font."""
    bench = data.get("benchmark", {})
    if not bench or "error" in bench or "alpha_pct" not in bench:
        return

    st.markdown("---")
    st.subheader("Benchmark Comparison (vs SPY)")

    def _fmt(val, suffix="", decimals=2):
        if val is None:
            return "N/A"
        return f"{val:.{decimals}f}{suffix}"

    metrics_html = f"""
    <div style="display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin:10px 0 18px 0;">
        <div style="background:#f7f9fb; border-radius:8px; padding:14px; border-left:4px solid #2E6B9E;">
            <div style="font-size:0.85em; color:#888;">Alpha (annualized)</div>
            <div style="{BENCHMARK_STYLE} font-size:1.35em;">{_fmt(bench.get('alpha_pct'), '%')}</div>
        </div>
        <div style="background:#f7f9fb; border-radius:8px; padding:14px; border-left:4px solid #2E6B9E;">
            <div style="font-size:0.85em; color:#888;">Beta</div>
            <div style="{BENCHMARK_STYLE} font-size:1.35em;">{_fmt(bench.get('beta'), '', 4)}</div>
        </div>
        <div style="background:#f7f9fb; border-radius:8px; padding:14px; border-left:4px solid #2E6B9E;">
            <div style="font-size:0.85em; color:#888;">Information Ratio</div>
            <div style="{BENCHMARK_STYLE} font-size:1.35em;">{_fmt(bench.get('information_ratio'), '', 4)}</div>
        </div>
        <div style="background:#f7f9fb; border-radius:8px; padding:14px; border-left:4px solid #2E6B9E;">
            <div style="font-size:0.85em; color:#888;">Sortino Ratio</div>
            <div style="{BENCHMARK_STYLE} font-size:1.35em;">{_fmt(bench.get('sortino_ratio'), '', 4)}</div>
        </div>
        <div style="background:#f7f9fb; border-radius:8px; padding:14px; border-left:4px solid #2E6B9E;">
            <div style="font-size:0.85em; color:#888;">Treynor Ratio</div>
            <div style="{BENCHMARK_STYLE} font-size:1.35em;">{_fmt(bench.get('treynor_ratio'), '', 4)}</div>
        </div>
    </div>
    <div style="{BENCHMARK_STYLE} font-size:0.95em; margin-bottom:8px;">
        SPY Cumulative Return: {_fmt(bench.get('benchmark_cumulative_return_pct'), '%')}
    </div>
    """
    st.markdown(metrics_html, unsafe_allow_html=True)


def render_risk_analysis(risk_data):
    """Render risk analysis results from the Risk Agent."""
    if not risk_data or "error" in risk_data:
        return

    label = risk_data.get("overfitting_label", "Unknown")
    score = risk_data.get("overfitting_score", 0)

    if score == 0:
        style = RISK_LOW_STYLE
        emoji = "&#9989;"
    elif score == 1:
        style = RISK_MOD_STYLE
        emoji = "&#9888;&#65039;"
    else:
        style = RISK_HIGH_STYLE
        emoji = "&#10060;"

    st.markdown(
        f'<div style="background:#f7f9fb; border-radius:8px; padding:16px; '
        f'border-left:5px solid {"#2E8B57" if score == 0 else "#D4A017" if score == 1 else "#C0392B"}; '
        f'margin-bottom:12px;">'
        f'<span style="font-size:1.3em;">{emoji}</span> '
        f'<span style="{style} font-size:1.3em;">Overfitting Risk: {label}</span>'
        f'<span style="color:#888; margin-left:12px;">(Score: {score}/3)</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # IS vs OOS comparison
    is_sum = risk_data.get("is_metrics_summary", {})
    oos_sum = risk_data.get("oos_metrics_summary", {})

    def _v(val, suffix=""):
        if val is None:
            return "N/A"
        return f"{val:.2f}{suffix}"

    st.markdown(
        f"""
        <table style="width:100%; border-collapse:collapse; margin:10px 0;">
            <tr style="background:#e8ecf0;">
                <th style="padding:8px; text-align:left;">Metric</th>
                <th style="padding:8px; text-align:center;">In-Sample (70%)</th>
                <th style="padding:8px; text-align:center;">Out-of-Sample (30%)</th>
            </tr>
            <tr>
                <td style="padding:8px;">Sharpe Ratio</td>
                <td style="padding:8px; text-align:center;">{_v(is_sum.get('sharpe_ratio'))}</td>
                <td style="padding:8px; text-align:center;">{_v(oos_sum.get('sharpe_ratio'))}</td>
            </tr>
            <tr style="background:#f7f9fb;">
                <td style="padding:8px;">Cumulative Return</td>
                <td style="padding:8px; text-align:center;">{_v(is_sum.get('cumulative_return_pct'), '%')}</td>
                <td style="padding:8px; text-align:center;">{_v(oos_sum.get('cumulative_return_pct'), '%')}</td>
            </tr>
            <tr>
                <td style="padding:8px;">Max Drawdown</td>
                <td style="padding:8px; text-align:center;">{_v(is_sum.get('max_drawdown_pct'), '%')}</td>
                <td style="padding:8px; text-align:center;">{_v(oos_sum.get('max_drawdown_pct'), '%')}</td>
            </tr>
        </table>
        """,
        unsafe_allow_html=True,
    )

    # Detailed stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        is_sharpe = risk_data.get("is_sharpe")
        is_sharpe_txt = f"{is_sharpe:.4f}" if is_sharpe is not None else "N/A"
        st.markdown(f"**IS Sharpe Ratio:**")
        st.markdown(f"`{is_sharpe_txt}`")
    with col2:
        oos_sharpe = risk_data.get("oos_sharpe")
        oos_sharpe_txt = f"{oos_sharpe:.4f}" if oos_sharpe is not None else "N/A"
        st.markdown(f"**OOS Sharpe Ratio:**")
        st.markdown(f"`{oos_sharpe_txt}`")
    with col3:
        decay = risk_data.get("sharpe_decay_ratio")
        decay_txt = f"{decay:.2f}" if decay is not None else "N/A"
        st.markdown(f"**Sharpe Decay (OOS/IS):**")
        st.markdown(f"`{decay_txt}`")
    with col4:
        calmar = risk_data.get("calmar_ratio_oos")
        calmar_txt = f"{calmar:.4f}" if calmar is not None else "N/A"
        st.markdown(f"**Calmar Ratio (OOS):**")
        st.markdown(f"`{calmar_txt}`")

    oos_trades = risk_data.get("oos_trade_count", "N/A")
    st.markdown(f"**OOS Trade Count:** `{oos_trades}` trades")

    # Flags
    flags = risk_data.get("flags", [])
    if flags:
        st.markdown("**Flags:**")
        for flag in flags:
            st.markdown(f"- ⚠️ {flag}")


# ── shared individual-ticker helpers ───────────────────────────────────────

def _render_individual_header(data, selectbox_key):
    """Section header + ticker selector. Returns (selected_ticker, ticker_df)."""
    st.markdown("---")
    st.markdown(
        '<h3 style="text-decoration:underline;"><b>Individual Ticker Analysis</b></h3>',
        unsafe_allow_html=True,
    )
    selected = st.selectbox("Ticker", data["tickers"], key=selectbox_key)
    tdf = pd.DataFrame(data["per_ticker_signal_rows"][selected])
    tdf["Date"] = pd.to_datetime(tdf["Date"])
    return selected, tdf


def _render_ticker_drawdown(ticker, tdf):
    if "drawdown" in tdf.columns:
        st.subheader(f"{ticker} Drawdown")
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=tdf["Date"], y=tdf["drawdown"] * 100,
                fill="tozeroy", name="Drawdown (%)",
                line=dict(color="red"),
            )
        )
        fig.update_layout(yaxis_title="Drawdown (%)", yaxis_ticksuffix="%")
        st.plotly_chart(fig, use_container_width=True)


def _render_ticker_metrics(data, ticker):
    if "per_ticker_metrics" in data and ticker in data["per_ticker_metrics"]:
        tm = data["per_ticker_metrics"][ticker]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Cumulative Return", f"{tm.get('cumulative_return_pct', 0):.2f}%")
        m2.metric("Max Drawdown", f"{tm.get('max_drawdown_pct', 0):.2f}%")
        m3.metric("Sharpe Ratio", f"{tm.get('sharpe_ratio', 0):.4f}")
        m4.metric("Trades", tm.get("number_of_trades", "-"))


def _render_buy_sell_markers(fig, tdf):
    buy_pts = tdf.dropna(subset=["buy_marker"])
    sell_pts = tdf.dropna(subset=["sell_marker"])
    fig.add_trace(go.Scatter(
        x=buy_pts["Date"], y=buy_pts["buy_marker"], mode="markers", name="Buy",
        marker=dict(symbol="triangle-up", size=12, color="green"),
    ))
    fig.add_trace(go.Scatter(
        x=sell_pts["Date"], y=sell_pts["sell_marker"], mode="markers", name="Sell",
        marker=dict(symbol="triangle-down", size=12, color="red"),
    ))


# ── Mean Reversion ─────────────────────────────────────────────────────────

def render_charts_mean_reversion(results):
    data = results

    _render_portfolio_section(data)

    selected, tdf = _render_individual_header(data, "mr_ticker_select")

    # Price + Bollinger Bands + signals
    st.subheader(f"{selected} Price & Trade Signals")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=tdf["Date"], y=tdf["Close"], name="Close"))
    if "bb_upper" in tdf.columns and "bb_lower" in tdf.columns:
        fig.add_trace(go.Scatter(
            x=tdf["Date"], y=tdf["bb_upper"], name="Upper BB",
            line=dict(color="orange"),
        ))
        fig.add_trace(go.Scatter(
            x=tdf["Date"], y=tdf["bb_lower"], name="Lower BB",
            line=dict(color="purple"),
        ))
    _render_buy_sell_markers(fig, tdf)
    st.plotly_chart(fig, use_container_width=True)

    # RSI chart
    if "rsi" in tdf.columns:
        st.subheader(f"{selected} RSI")
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(x=tdf["Date"], y=tdf["rsi"], name="RSI", line=dict(color="blue")))
        fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold")
        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought")
        fig_rsi.update_layout(yaxis_title="RSI", yaxis=dict(range=[0, 100]))
        st.plotly_chart(fig_rsi, use_container_width=True)

    _render_ticker_drawdown(selected, tdf)
    _render_ticker_metrics(data, selected)


# ── Trend Follower ─────────────────────────────────────────────────────────

def render_charts_trend(results):
    data = results

    _render_portfolio_section(data)

    selected, tdf = _render_individual_header(data, "tf_ticker_select")

    # Price + EMA + signals
    st.subheader(f"{selected} Price + EMA Cross Signals")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=tdf["Date"], y=tdf["Close"], name="Close"))
    fig.add_trace(go.Scatter(x=tdf["Date"], y=tdf["ema_fast"], name="Fast EMA"))
    fig.add_trace(go.Scatter(x=tdf["Date"], y=tdf["ema_slow"], name="Slow EMA"))
    _render_buy_sell_markers(fig, tdf)
    st.plotly_chart(fig, use_container_width=True)

    # ADX chart
    st.subheader(f"{selected} ADX")
    fig_adx = go.Figure()
    fig_adx.add_trace(go.Scatter(x=tdf["Date"], y=tdf["adx"], name="ADX"))
    fig_adx.add_trace(go.Scatter(
        x=tdf["Date"], y=tdf["adx_threshold"], name="ADX Threshold",
        line=dict(dash="dash"),
    ))
    st.plotly_chart(fig_adx, use_container_width=True)

    _render_ticker_drawdown(selected, tdf)
    _render_ticker_metrics(data, selected)


# ── Volatility Breakout (MACD) ────────────────────────────────────────────

def render_charts_breakout(results):
    data = results

    _render_portfolio_section(data)

    selected, tdf = _render_individual_header(data, "macd_ticker_select")

    # Price + signals
    st.subheader(f"{selected} Price & Trade Signals")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=tdf["Date"], y=tdf["Close"], name="Close"))
    _render_buy_sell_markers(fig, tdf)
    st.plotly_chart(fig, use_container_width=True)

    _render_ticker_drawdown(selected, tdf)
    _render_ticker_metrics(data, selected)


# ── AI Insights ────────────────────────────────────────────────────────────

_CARD_CSS = (
    "border-radius:8px; padding:14px; margin-bottom:16px; "
    "font-size:0.92em; line-height:1.7; color:#1a1a1a;"
)


def _md_to_html(text: str) -> str:
    """Convert markdown text from the LLM into clean HTML."""
    return markdown.markdown(
        text,
        extensions=["extra", "sane_lists", "nl2br"],
    )


def _render_insight_card(title: str, body_md: str, bg: str, accent: str):
    """Render a single AI insight card with proper markdown→HTML conversion."""
    st.markdown(
        f'<p style="font-size:1.05em; font-weight:600; margin-bottom:4px;">{title}</p>',
        unsafe_allow_html=True,
    )
    body_html = _md_to_html(body_md)
    st.markdown(
        f'<div style="background:{bg}; border-left:4px solid {accent}; {_CARD_CSS}">'
        f'{body_html}</div>',
        unsafe_allow_html=True,
    )


def render_ai_insights(insights_data):
    """Render AI-generated insights from Cohere."""
    if not insights_data:
        return

    perf = insights_data.get("performance_insights", "")
    if perf:
        _render_insight_card("Performance Insights", perf, "#f0f5fa", "#2E6B9E")

    risk = insights_data.get("risk_insights", "")
    if risk:
        _render_insight_card("Risk Insights", risk, "#fdf6f0", "#D4A017")

    guidance = insights_data.get("actionable_guidance", "")
    if guidance:
        _render_insight_card("Actionable Guidance", guidance, "#f0faf0", "#2E8B57")