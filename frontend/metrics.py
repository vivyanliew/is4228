
import streamlit as st
import pandas as pd

def render_metrics(results):

    data = results

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Portfolio Metrics")
        # st.json(data["portfolio_metrics"])
        # df = pd.DataFrame(data["portfolio_metrics"].items(), columns=["Metric", "Value"])
        # st.dataframe(df, use_container_width=True, hide_index=True)

        metrics_raw = data["portfolio_metrics"]
        # rename + format
        metrics_clean = {
            "Initial Capital": f"${metrics_raw['initial_capital']:,.0f}",
            "Final Equity": f"${metrics_raw['final_equity']:,.2f}",
            "Cumulative Return": f"{metrics_raw['cumulative_return_pct']:.2f}%",
            "Annualized Return": f"{metrics_raw['annualized_return_pct']:.2f}%",
            "Volatility (Annualized)": f"{metrics_raw['annualized_volatility_pct']:.2f}%",
            "Sharpe Ratio": f"{metrics_raw['sharpe_ratio']:.2f}",
            "Max Drawdown": f"{metrics_raw['max_drawdown_pct']:.2f}%"
        }

        df_display = pd.DataFrame(metrics_clean.items(), columns=["Metric", "Value"])

        # Color styling
        def color_values(val):
            if "%" in val:
                num = float(val.replace("%", ""))
                if num > 0:
                    return "color: green"
                elif num < 0:
                    return "color: red"
            return ""

        styled_df = df_display.style.applymap(color_values, subset=["Value"])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)

    with col2:
        st.subheader("Per-Ticker Metrics")
        
        ticker_metrics_raw = data["per_ticker_metrics"]
        # st.json(ticker_metrics_raw)
        # rename + format
        rename_map = {
            "initial_capital": "Initial Capital",
            "final_equity": "Final Equity",
            "cumulative_return_pct": "Cumulative Return",
            "annualized_return_pct": "Annualized Return",
            "annualized_volatility_pct": "Volatility (Annualized)",
            "sharpe_ratio": "Sharpe Ratio",
            "max_drawdown_pct": "Max Drawdown",
            "number_of_trades": "Number of trades",
            "win_rate_pct": "Win Rate"
        }

        rows = []

        for ticker, metrics in ticker_metrics_raw.items():
            row = {"Ticker": ticker}
            
            for k, v in metrics.items():
                clean_key = rename_map.get(k, k)
                
                # formatting
                if v is None: #handle missing values
                    row[clean_key] = "-"
                    continue
                if "equity" in k or "capital" in k:
                    row[clean_key] = f"${v:,.2f}"
                elif "pct" in k:
                    row[clean_key] = f"{v:.2f}%"
                elif "sharpe" in k:
                    row[clean_key] = f"{v:.2f}"
                else:
                    row[clean_key] = v
                # row[clean_key] = v
            
            rows.append(row)

        df_display = pd.DataFrame(rows)
        def color_vals(val):
            
            if isinstance(val, str) and "%" in val:
                num = float(val.replace("%", ""))
                if num > 0:
                    return "color: green"
                elif num < 0:
                    return "color: red"
                
            # Case 2: raw float (fallback safety)
            else:
                num = val
 
            return ""
        
        styled_df = df_display.style.applymap(color_vals)
        st.dataframe(styled_df, use_container_width=True, hide_index=True)

        # per_ticker_df = pd.DataFrame(ticker_metrics_raw).T.reset_index()
        # per_ticker_df = per_ticker_df.rename(columns={"index": "ticker"})
        # # styled_ticker_df = per_ticker_df.style.applymap(color_values, subset = [""])
        # st.dataframe(per_ticker_df, use_container_width=True)