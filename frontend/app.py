import streamlit as st
# from data import load_data
# from indicators import compute_indicators
# from strategy import generate_signals
# from backtest import run_backtest
# from metrics import compute_metrics

# from frontend.sidebar import render_sidebar
# from frontend.charts import render_charts
# from frontend.metrics import render_metrics

st.set_page_config(page_title="Strategy Backtester", layout="wide")

st.title("📊 Strategy Research & Backtesting Tool")

# -------------------------
# Sidebar Inputs
# -------------------------
# params = render_sidebar()

# -------------------------
# Run Pipeline
# -------------------------
# if st.button("Run Backtest"):

#     df = load_data(params["ticker"], params["start"], params["end"])
#     df = compute_indicators(df, params)
#     df = generate_signals(df, params)

#     results = run_backtest(df)
#     metrics = compute_metrics(results)

#     results["data"] = df
#     results["metrics"] = metrics

#     # -------------------------
#     # Layout
#     # -------------------------
#     col1, col2 = st.columns([3, 1])

#     with col1:
#         render_charts(results)

#     with col2:
#         render_metrics(results)