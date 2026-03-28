import numpy as np
import pandas as pd


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