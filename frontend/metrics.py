import streamlit as st
import pandas as pd

def render_metrics_mean_reversion(results):

    data = results

    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Portfolio Metrics")
        metrics_raw = data["portfolio_metrics"]
        # rename + format
        metrics_clean = {
            "Initial Capital": f"${metrics_raw['initial_capital']:,.0f}",
            "Final Equity": f"${metrics_raw['final_equity']:,.2f}",
            "Cumulative Return": f"{metrics_raw['cumulative_return_pct']:.2f}%",
            "Annualized Return": f"{metrics_raw['annualized_return_pct']:.2f}%",
            "Volatility (Annualized)": f"{metrics_raw['annualized_volatility_pct']:.2f}%",
            "Sharpe Ratio": f"{metrics_raw['sharpe_ratio']:.4f}",
            "Max Drawdown": f"{metrics_raw['max_drawdown_pct']:.2f}%"
        }

        df_display = pd.DataFrame(metrics_clean.items(), columns=["Metric", "Value"])

        styled_df = df_display.style.apply(color_metrics, axis=1)
        st.table(styled_df)

    with col2:
        st.subheader("Per-Ticker Metrics")
        
        ticker_metrics_raw = data["per_ticker_metrics"]

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
                    row[clean_key] = f"{v:.4f}"
                else:
                    row[clean_key] = v
            
            rows.append(row)
        
        df_display = pd.DataFrame(rows)
        styled_df = df_display.style.applymap(color_vals, subset = ["Cumulative Return","Annualized Return","Max Drawdown"])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)

def render_metrics_trend(results):
    
    data = results

    return 

def render_metrics_breakout(results):
    
    data = results

    st.subheader("Metrics")
    col1, col2 = st.columns([1, 2])

    with col1:
        metrics = data["metrics"]
        metrics_clean = {
            "Initial Capital": f"${metrics['initial_capital']:,.0f}",
            "Final Equity": f"${metrics['final_equity']:,.2f}",
            "Cumulative Return": f"{metrics['cumulative_return_pct']:.2f}%",
            "Annualized Return": f"{metrics['annualized_return_pct']:.2f}%",
            "Volatility (Annualized)": f"{metrics['annualized_volatility_pct']:.2f}%",
            "Sharpe Ratio": f"{metrics['sharpe_ratio']:.4f}",
            "Max Drawdown": f"{metrics['max_drawdown_pct']:.2f}%",
            "Number Of Trades": f"{metrics['number_of_trades']:,.0f}",
            "Win Rate": f"{metrics['win_rate_pct']:.2f}%"
        }
        df_metrics = pd.DataFrame(metrics_clean.items(), columns=["Metric", "Value"])

        styled_df = df_metrics.style.apply(color_metrics, axis=1)
        st.table(styled_df)

    with col2: 
        st.subheader("Trades")
        if data["trades"]:
            trade_metrics = data["trades"] # dicts within list 
            # st.json(trade_metrics)
            # rename + format
            rename_map = {
                "entry_date": "Entry Date",
                "entry_price": "Entry Price",
                "exit_date": "Exit Date",
                "exit_price": "Exit Price",
                "return_pct": "Return"
            }

            rows = []
            for trades in trade_metrics:
                row = {}
                for k, v in trades.items():
                    clean_key = rename_map.get(k, k)
                    # formatting
                    if v is None: #handle missing values
                        row[clean_key] = "-"
                        continue
                    if "price" in k:
                        row[clean_key] = f"${v:,.2f}"
                    elif "pct" in k:
                        row[clean_key] = f"{v:.2f}%"
                    else:
                        row[clean_key] = v
                
                rows.append(row)

            trades_df = pd.DataFrame(rows)
            trades_df_styled = trades_df.style.applymap(color_vals)
            st.dataframe(trades_df_styled, use_container_width=True, hide_index=True)
        else:
            st.info("No trades executed")


        

#### Helper Functions
def color_metrics(row):
    val = row["Value"]
    metric = row["Metric"]
    
    # Check if it's a percentage AND not a Volatility metric
    if "%" in val and "Volatility" not in metric and "Win" not in metric:
        num = float(val.replace("%", ""))
        if num > 0:
            return ["", "color: green"]
        elif num < 0:
            return ["", "color: red"]
            
    return ["", ""] # No style for either column


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