from pathlib import Path
import sys
import requests
import streamlit as st

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.agents.backtest_agent import BacktestAgent
from app.agents.market_context_agent import MarketContextAgent
from app.agents.optimization_agent import OptimizationAgent
from app.agents.report_agent import ReportAgent
from app.agents.risk_agent import RiskAgent


st.set_page_config(page_title="Agent Report Test")
st.title("Agent Report Test")

API_BASE = "http://127.0.0.1:8000"
ticker = st.text_input("Ticker", value="AAPL")
start_date = st.text_input("Start Date", value="2022-01-01")
end_date = st.text_input("End Date", value="2024-12-31")

strategy_name = "macd"
strategy_params = {
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "bb_window": 20,
    "bb_std": 2.0,
    "squeeze_quantile_window": 20,
    "squeeze_threshold_quantile": 0.2,
}
param_grid = {
    "macd_fast": [10, 12],
    "macd_slow": [24, 26],
    "macd_signal": [9],
    "bb_window": [20],
    "bb_std": [2.0],
    "squeeze_quantile_window": [20],
    "squeeze_threshold_quantile": [0.2],
}
strategy_specs = [{"strategy": "MACD", "params": strategy_params}]

if st.button("Run Report Agent"):
    try:
        with st.spinner("Collecting all data and running report agent..."):
            # market_context = MarketContextAgent().run(
            #     ticker=ticker,
            #     start_date=start_date,
            #     end_date=end_date,
            # )
            market_context = requests.post(
                f"{API_BASE}/agent/market-context",
                json={
                    "ticker": ticker,
                    "start_date": start_date,
                    "end_date": end_date,
                }
            ).json()
            # backtest_results = BacktestAgent().run(
            #     ticker=ticker,
            #     start_date=start_date,
            #     end_date=end_date,
            #     strategy_name=strategy_name,
            #     strategy_params=strategy_params,
            #     initial_capital=10000.0,
            #     is_split=0.7,
            # )
            backtest_results_res = requests.post(
                f"{API_BASE}/agent/backtest",
                json={
                    "ticker": ticker,
                    "start_date": start_date,
                    "end_date": end_date,
                    "strategy_name": strategy_name,
                    "strategy_params": strategy_params,
                    "initial_capital": 10000.0,
                    "is_split": 0.7,
                }
            )
            backtest_results = backtest_results_res.json()
            risk_results = backtest_results["risk_report"]

            # optimization_results = OptimizationAgent().run(
            #     ticker=ticker,
            #     start_date=start_date,
            #     end_date=end_date,
            #     strategy_name=strategy_name,
            #     param_grid=param_grid,
            #     initial_capital=10000.0,
            #     is_split=0.7,
            #     top_n=3,
            # )["top_configs"]
            optimization_results = requests.post(
                f"{API_BASE}/agent/optimize",
                json={
                    "ticker": ticker,
                    "start_date": start_date,
                    "end_date": end_date,
                    "strategy_name": strategy_name,
                    "param_grid": param_grid,
                    "initial_capital": 10000.0,
                    "is_split": 0.7,
                    "top_n": 5,
                }
            ).json()

            payload = {
                "ticker": ticker,
                "start_date": start_date,
                "end_date": end_date,
                "market_context": market_context,
                "strategy_specs": strategy_specs,
                "backtest_results": backtest_results,
                "risk_results": risk_results,
                "optimization_results": optimization_results["top_configs"],
            }

            response = requests.post(
                    f"{API_BASE}/agent/report",
                    json=payload
                )
            data = response.json()

            st.subheader("Strategy Research Report")
            if response.status_code != 200:
                st.error(data.get("detail", "Report request failed"))
                st.json(data)
            else:
                if data["warnings"]:
                    with st.expander("Warnings", expanded=True):
                        for warning in data["warnings"]:
                            st.warning(warning)

                if data["summary"]:
                    st.info(data["summary"])

                section_order = [
                    "Market Context",
                    "Strategy Overview",
                    "Backtest Performance",
                    "Risk Analysis",
                    "Parameter Recommendations",
                    "Risk Warnings",
                    "Conclusion",
                ]

                rendered = set()
                for key in section_order:
                    if key in data["sections"]:
                        with st.expander(key, expanded=(key == "Backtest Performance")):
                            st.markdown(data["sections"][key])
                        rendered.add(key)

                for key, content in data["sections"].items():
                    if key not in rendered and key != "Executive Summary":
                        with st.expander(key):
                            st.markdown(content)

                with st.expander("Full Markdown"):
                    st.markdown(data["markdown"])

    except Exception as exc:
        st.error(f"Error: {exc}")
