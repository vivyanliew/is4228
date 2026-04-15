import numpy as np
import pandas as pd
import yfinance as yf


def compute_portfolio_metrics(portfolio_df: pd.DataFrame, initial_capital: float):
    strategy_eq = portfolio_df["portfolio_strategy_eq"]
    strategy_returns = strategy_eq.pct_change().dropna()

    final_equity = float(strategy_eq.iloc[-1])
    cumulative_return = (final_equity / initial_capital) - 1

    if len(strategy_returns) > 0:
        annualized_return = (strategy_eq.iloc[-1] / strategy_eq.iloc[0]) ** (252 / len(strategy_returns)) - 1
        annualized_vol = strategy_returns.std() * np.sqrt(252)
        sharpe_ratio = annualized_return / annualized_vol if annualized_vol > 0 else np.nan
    else:
        annualized_return = np.nan
        annualized_vol = np.nan
        sharpe_ratio = np.nan

    peak = strategy_eq.cummax()
    drawdown = strategy_eq / peak - 1.0
    max_drawdown = drawdown.min()

    metrics = {
        "initial_capital": round(initial_capital, 2),
        "final_equity": round(final_equity, 2),
        "cumulative_return_pct": round(cumulative_return * 100, 2),
        "annualized_return_pct": round(annualized_return * 100, 2) if not pd.isna(annualized_return) else None,
        "annualized_volatility_pct": round(annualized_vol * 100, 2) if not pd.isna(annualized_vol) else None,
        "sharpe_ratio": round(sharpe_ratio, 4) if not pd.isna(sharpe_ratio) else None,
        "max_drawdown_pct": round(max_drawdown * 100, 2) if not pd.isna(max_drawdown) else None,
    }

    return metrics


def compute_benchmark_metrics(
    portfolio_df: pd.DataFrame,
    initial_capital: float,
    start_date: str,
    end_date: str,
    benchmark_ticker: str = "SPY",
) -> dict:
    """Fetch SPY data and compute benchmark-relative metrics."""

    # Fetch benchmark price data
    bench_df = yf.download(benchmark_ticker, start=start_date, end=end_date, auto_adjust=False)
    if bench_df.empty:
        return {"error": f"No data for {benchmark_ticker}"}

    if isinstance(bench_df.columns, pd.MultiIndex):
        bench_df.columns = bench_df.columns.get_level_values(0)
    bench_df = bench_df.reset_index()

    # Build benchmark equity curve scaled to same initial capital
    bench_df["bench_return"] = bench_df["Close"].pct_change().fillna(0)
    bench_df["bench_eq"] = initial_capital * (1 + bench_df["bench_return"]).cumprod()

    # Align dates
    port_dates = pd.to_datetime(portfolio_df["Date"])
    bench_dates = pd.to_datetime(bench_df["Date"])
    common_dates = sorted(set(port_dates) & set(bench_dates))

    if len(common_dates) < 10:
        return {"error": "Insufficient overlapping dates with benchmark"}

    port_aligned = portfolio_df[port_dates.isin(common_dates)].reset_index(drop=True)
    bench_aligned = bench_df[bench_dates.isin(common_dates)].reset_index(drop=True)

    # Returns
    strat_returns = port_aligned["portfolio_strategy_eq"].pct_change().dropna().values
    bench_returns = bench_aligned["bench_eq"].pct_change().dropna().values
    min_len = min(len(strat_returns), len(bench_returns))
    strat_returns = strat_returns[:min_len]
    bench_returns = bench_returns[:min_len]

    # Beta & Alpha (CAPM)
    cov_matrix = np.cov(strat_returns, bench_returns)
    beta = cov_matrix[0, 1] / cov_matrix[1, 1] if cov_matrix[1, 1] != 0 else np.nan
    ann_strat = np.mean(strat_returns) * 252
    ann_bench = np.mean(bench_returns) * 252
    rf_rate = 0.04  # approximate risk-free rate
    alpha = ann_strat - (rf_rate + beta * (ann_bench - rf_rate)) if not np.isnan(beta) else np.nan

    # Information Ratio
    excess = strat_returns - bench_returns
    tracking_error = np.std(excess) * np.sqrt(252) if len(excess) > 1 else np.nan
    info_ratio = (np.mean(excess) * 252) / tracking_error if tracking_error > 0 else np.nan

    # Sortino Ratio (strategy standalone)
    downside = strat_returns[strat_returns < 0]
    downside_std = np.std(downside) * np.sqrt(252) if len(downside) > 1 else np.nan
    sortino = (ann_strat - rf_rate) / downside_std if downside_std and downside_std > 0 else np.nan

    # Treynor Ratio
    treynor = (ann_strat - rf_rate) / beta if beta and beta != 0 else np.nan

    # Benchmark cumulative return
    bench_cum = (bench_aligned["bench_eq"].iloc[-1] / bench_aligned["bench_eq"].iloc[0] - 1) * 100

    # Benchmark equity rows for the chart
    bench_rows = bench_aligned[["Date", "bench_eq"]].copy()
    bench_rows["Date"] = bench_rows["Date"].dt.strftime("%Y-%m-%d")

    def _safe(v):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return None
        return round(float(v), 4)

    return {
        "alpha_pct": _safe(alpha * 100) if alpha is not None and not np.isnan(alpha) else None,
        "beta": _safe(beta),
        "information_ratio": _safe(info_ratio),
        "tracking_error_pct": _safe(tracking_error * 100) if tracking_error is not None and not np.isnan(tracking_error) else None,
        "sortino_ratio": _safe(sortino),
        "treynor_ratio": _safe(treynor),
        "benchmark_cumulative_return_pct": _safe(bench_cum),
        "benchmark_ticker": benchmark_ticker,
        "benchmark_equity_rows": bench_rows.to_dict(orient="records"),
    }