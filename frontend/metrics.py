import streamlit as st

def render_metrics(results):
    #render the performance metrics panel 
    #extract metrics safely from results
    metrics = results.get("metrics", {})
    #header
    st.subheader("Performance Metrics")

    #2 columns for layout
    col1, col2 = st.columns(2)

    with col1:
        st.metric("Total Return", f"{metrics.get('total_return', 0):.2%}")
        st.metric("Sharpe Ratio", f"{metrics.get('sharpe_ratio', 0):.2f}")

    with col2:
        st.metric("Max Drawdown", f"{metrics.get('max_drawdown', 0):.2%}")
        st.metric("Win Rate", f"{metrics.get('win_rate', 0):.2%}")

#TEMPORARY: demo data for testing frontend [to be removed when backend ready]
if st.button("Run Backtest (Demo)"):
    #dummy results for frontend testing
    demo_results = {
        "metrics": {
            "total_return": 0.18,
            "sharpe_ratio": 1.2,
            "max_drawdown": -0.10,
            "win_rate": 0.55,
            "num_trades": 42
        }
    }

    #render metrics panel
    render_metrics(demo_results)
