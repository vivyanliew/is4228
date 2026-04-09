"""
Agent Walk-Forward & Optimizer Test UI
Run from the backend/ directory:
    streamlit run app/test_frontend_agent.py
FastAPI must be running on http://127.0.0.1:8000
"""

import streamlit as st
import requests
import pandas as pd

API_BASE = "http://127.0.0.1:8000"

st.set_page_config(page_title="Agent Backtest Tester", layout="wide")
st.title("AI Agent — Walk-Forward Backtest & Optimizer")

# ---------------------------------------------------------------------------
# Shared inputs
# ---------------------------------------------------------------------------
st.sidebar.header("Common Inputs")
ticker = st.sidebar.text_input("Ticker", value="AAPL")
start_date = st.sidebar.text_input("Start Date", value="2015-01-01")
end_date = st.sidebar.text_input("End Date", value="2025-01-01")
initial_capital = st.sidebar.number_input("Initial Capital", value=10000.0, min_value=100.0)
is_split = st.sidebar.slider("IS / OOS Split", min_value=0.3, max_value=0.9, value=0.7, step=0.05,
                              help="Fraction of data used as in-sample. Remainder is out-of-sample.")

strategy = st.sidebar.selectbox("Strategy", ["mean_reversion", "trend_follower", "macd"])

# ---------------------------------------------------------------------------
# Default parameters per strategy
# ---------------------------------------------------------------------------
DEFAULT_PARAMS = {
    "mean_reversion": {"bb_window": 20, "bb_std": 2.0, "rsi_window": 14, "rsi_entry": 30.0, "rsi_exit": 70.0},
    "trend_follower": {"ema_fast": 20, "ema_slow": 50, "adx_window": 14, "adx_threshold": 25.0},
    "macd":           {"macd_fast": 12, "macd_slow": 26, "macd_signal": 9, "bb_window": 20,
                       "bb_std": 2.0, "squeeze_quantile_window": 20, "squeeze_threshold_quantile": 0.2},
}

# Default param_grid per strategy (for optimizer section)
DEFAULT_GRIDS = {
    "mean_reversion": '{"bb_window": [15, 20, 25], "bb_std": [1.5, 2.0, 2.5], "rsi_window": [14], "rsi_entry": [25.0, 30.0], "rsi_exit": [70.0, 75.0]}',
    "trend_follower": '{"ema_fast": [10, 20], "ema_slow": [40, 50], "adx_window": [14], "adx_threshold": [20.0, 25.0]}',
    "macd":           '{"macd_fast": [10, 12], "macd_slow": [24, 26], "macd_signal": [9], "bb_window": [18, 20, 22], "bb_std": [2.0], "squeeze_quantile_window": [20], "squeeze_threshold_quantile": [0.2]}',
}

tab1, tab2 = st.tabs(["Walk-Forward Backtest", "Optimizer"])

# ===========================================================================
# TAB 1 — Walk-Forward Backtest
# ===========================================================================
with tab1:
    st.subheader("Walk-Forward Backtest")
    st.caption("Splits data into IS (training) and OOS (validation) windows, runs the same fixed parameters on both, and assesses overfitting risk.")

    st.markdown("#### Strategy Parameters")
    params_input = st.text_area(
        "Parameters (JSON)",
        value=str(DEFAULT_PARAMS[strategy]).replace("'", '"'),
        height=80,
    )

    if st.button("Run Walk-Forward Backtest", type="primary"):
        import json
        try:
            params = json.loads(params_input)
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON in parameters: {e}")
            st.stop()

        payload = {
            "ticker": ticker,
            "start_date": start_date,
            "end_date": end_date,
            "initial_capital": float(initial_capital),
            "strategy_name": strategy,
            "strategy_params": params,
            "is_split": float(is_split),
        }

        with st.spinner("Running walk-forward backtest..."):
            try:
                resp = requests.post(f"{API_BASE}/agent/backtest", json=payload, timeout=60)
            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to FastAPI at http://127.0.0.1:8000 — make sure the server is running.")
                st.stop()

        if resp.status_code != 200:
            st.error(f"API error {resp.status_code}")
            st.json(resp.json())
        else:
            data = resp.json()
            risk = data["risk_report"]
            is_metrics = data["is_metrics"]
            oos_metrics = data["oos_metrics"]

            # --- Date split info ---
            st.info(
                f"**IS window**: {start_date} → {data['is_end_date']}   |   "
                f"**OOS window**: {data['oos_start_date']} → {end_date}"
            )

            # --- Risk banner ---
            score = risk["overfitting_score"]
            label = risk["overfitting_label"]
            if score == 0:
                st.success(f"Overfitting Risk: **{label}** (score {score}/3)")
            elif score == 1:
                st.warning(f"Overfitting Risk: **{label}** (score {score}/3)")
            else:
                st.error(f"Overfitting Risk: **{label}** (score {score}/3)")

            if risk["flags"]:
                with st.expander("Risk Flags", expanded=True):
                    for flag in risk["flags"]:
                        st.markdown(f"- {flag}")

            # --- IS vs OOS metrics side-by-side ---
            st.markdown("#### Performance Comparison")

            metric_keys = [
                ("cumulative_return_pct", "Cumulative Return (%)"),
                ("annualized_return_pct", "Annualized Return (%)"),
                ("sharpe_ratio",          "Sharpe Ratio"),
                ("max_drawdown_pct",      "Max Drawdown (%)"),
                ("annualized_volatility_pct", "Annual Vol (%)"),
                ("number_of_trades",      "# Trades"),
                ("win_rate_pct",          "Win Rate (%)"),
            ]

            col_is, col_oos = st.columns(2)
            with col_is:
                st.markdown("**In-Sample (IS)**")
                for key, label_str in metric_keys:
                    v = is_metrics.get(key)
                    st.metric(label_str, f"{v:.2f}" if isinstance(v, float) else str(v) if v is not None else "N/A")

            with col_oos:
                st.markdown("**Out-of-Sample (OOS)**")
                for key, label_str in metric_keys:
                    v_oos = oos_metrics.get(key)
                    v_is  = is_metrics.get(key)
                    display = f"{v_oos:.2f}" if isinstance(v_oos, float) else str(v_oos) if v_oos is not None else "N/A"
                    if isinstance(v_oos, (int, float)) and isinstance(v_is, (int, float)) and v_is != 0:
                        delta = round(float(v_oos) - float(v_is), 2)
                        st.metric(label_str, display, delta=delta)
                    else:
                        st.metric(label_str, display)

            # --- Extra risk ratios ---
            st.markdown("#### Risk Ratios (OOS)")
            rc1, rc2, rc3 = st.columns(3)
            rc1.metric("Sharpe Decay (OOS/IS)", f"{risk['sharpe_decay_ratio']:.2f}" if risk["sharpe_decay_ratio"] is not None else "N/A")
            rc2.metric("Calmar Ratio (OOS)", f"{risk['calmar_ratio_oos']:.2f}" if risk["calmar_ratio_oos"] is not None else "N/A")
            rc3.metric("OOS Trade Count", str(risk["oos_trade_count"]))

            # --- Trade logs ---
            st.markdown("#### Trade Logs")
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                st.caption("IS Trades")
                if data["is_trades"]:
                    st.dataframe(pd.DataFrame(data["is_trades"]), use_container_width=True, hide_index=True)
                else:
                    st.info("No IS trades")
            with col_t2:
                st.caption("OOS Trades")
                if data["oos_trades"]:
                    st.dataframe(pd.DataFrame(data["oos_trades"]), use_container_width=True, hide_index=True)
                else:
                    st.info("No OOS trades")

            # --- Raw response ---
            with st.expander("Raw API Response"):
                st.json(data)

# ===========================================================================
# TAB 2 — Optimizer
# ===========================================================================
with tab2:
    st.subheader("Parameter Grid Optimizer")
    st.caption(
        "Define a grid of values per parameter. The optimizer runs a walk-forward backtest "
        "for every combination, filters out overfitting or data-thin configs, "
        "and ranks the rest by a composite OOS score."
    )
    st.warning("Keep grids small (2–4 values per param) to avoid long runtimes. "
               "Example: 3 params × 3 values each = 27 backtests.")

    param_grid_input = st.text_area(
        "Parameter Grid (JSON dictionary: param → list of values)",
        value=DEFAULT_GRIDS[strategy],
        height=130,
    )

    if st.button("Run Optimizer", type="primary"):
        import json
        try:
            param_grid = json.loads(param_grid_input)
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e}")
            st.stop()

        # Estimate grid size
        import itertools
        grid_size = 1
        for vals in param_grid.values():
            grid_size *= len(vals)
        st.info(f"Grid size: **{grid_size} candidates**")

        payload = {
            "ticker": ticker,
            "start_date": start_date,
            "end_date": end_date,
            "initial_capital": float(initial_capital),
            "strategy_name": strategy,
            "param_grid": param_grid,
            "is_split": float(is_split),
        }

        with st.spinner(f"Optimizing {grid_size} candidates — this may take a while..."):
            try:
                resp = requests.post(f"{API_BASE}/agent/optimize", json=payload, timeout=300)
            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to FastAPI at http://127.0.0.1:8000")
                st.stop()

        if resp.status_code != 200:
            st.error(f"API error {resp.status_code}")
            st.json(resp.json())
        else:
            data = resp.json()

            # --- Summary stats ---
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Total Candidates", data["total_candidates"])
            s2.metric("Passed Filters", data["passed"])
            s3.metric("Skipped (low quality)", data["skipped"])
            s4.metric("Errors", data["errors"])

            top = data["top_configs"]
            if not top:
                st.error("No candidates passed the quality filters. "
                         "Try a wider date range, different strategy, or looser grid.")
            else:
                st.markdown(f"#### Top {len(top)} Configurations (ranked by OOS composite score)")

                # Build display table
                rows = []
                for rank, cfg in enumerate(top, 1):
                    row = {"Rank": rank, "Score": round(cfg["score"], 4)}
                    row.update(cfg["params"])
                    oos = cfg["oos_metrics"]
                    is_ = cfg["is_metrics"]
                    row["OOS Sharpe"] = oos.get("sharpe_ratio")
                    row["OOS CumRet%"] = oos.get("cumulative_return_pct")
                    row["OOS MaxDD%"] = oos.get("max_drawdown_pct")
                    row["OOS Trades"] = oos.get("number_of_trades")
                    row["IS Sharpe"]  = is_.get("sharpe_ratio")
                    row["Risk Label"] = cfg["risk_report"]["overfitting_label"]
                    rows.append(row)

                results_df = pd.DataFrame(rows)

                def color_risk(val):
                    if val == "Low Risk":
                        return "background-color: #d4edda; color: #155724"
                    elif val == "Moderate Risk":
                        return "background-color: #fff3cd; color: #856404"
                    else:
                        return "background-color: #f8d7da; color: #721c24"

                styled = results_df.style.applymap(color_risk, subset=["Risk Label"])
                st.dataframe(styled, use_container_width=True, hide_index=True)

                # --- Detailed drill-down ---
                st.markdown("#### Drill-Down: IS vs OOS per Config")
                for rank, cfg in enumerate(top, 1):
                    with st.expander(f"Rank {rank} — Score: {cfg['score']:.4f} | Params: {cfg['params']}"):
                        dc1, dc2 = st.columns(2)
                        with dc1:
                            st.caption("In-Sample")
                            st.json(cfg["is_metrics"])
                        with dc2:
                            st.caption("Out-of-Sample")
                            st.json(cfg["oos_metrics"])
                        st.caption("Risk Report")
                        rr = cfg["risk_report"]
                        st.write(f"**{rr['overfitting_label']}** (score {rr['overfitting_score']}/3) "
                                 f"| Sharpe Decay: {rr['sharpe_decay_ratio']} "
                                 f"| Calmar (OOS): {rr['calmar_ratio_oos']}")
                        if rr["flags"]:
                            for flag in rr["flags"]:
                                st.markdown(f"- {flag}")

            with st.expander("Raw API Response"):
                st.json(data)
