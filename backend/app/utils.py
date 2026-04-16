"""
Shared utilities used by both routers.py and the agent layer.
Extracted here to avoid circular imports.
"""
import numpy as np
import pandas as pd
import yfinance as yf

from app.strategies.strategy_ema import run_strategy as run_ema_strategy
from app.strategies.strategy_macd import run_strategy as run_macd_strategy
from app.strategies.strategy_macd_volume_confirmation import (
    run_strategy as run_macd_volume_confirmation_strategy,
)
from app.strategies.strategy_mean_reversion import run_strategy as run_mean_reversion_strategy
from app.strategies.strategy_rsi_adx_filter import run_strategy as run_rsi_adx_filter_strategy
from app.strategies.strategy_rsi_volume_filter import (
    run_strategy as run_rsi_volume_filter_strategy,
)


def fetch_price_data(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    price_df = yf.download(ticker, start=start_date, end=end_date, auto_adjust=False)

    if price_df.empty:
        raise ValueError(f"No price data found for ticker {ticker}")

    if isinstance(price_df.columns, pd.MultiIndex):
        price_df.columns = price_df.columns.get_level_values(0)

    price_df = price_df.reset_index()

    required_cols = ["Date", "Open", "High", "Low", "Close", "Volume"]
    missing_cols = [col for col in required_cols if col not in price_df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns in price data: {missing_cols}")

    return price_df


def run_strategy_by_name(strategy_name: str, price_df: pd.DataFrame, strategy_params: dict) -> pd.DataFrame:
    if strategy_name == "macd":
        return run_macd_strategy(price_df, strategy_params)
    if strategy_name == "mean_reversion":
        return run_mean_reversion_strategy(price_df, strategy_params)
    if strategy_name == "trend_follower":
        return run_ema_strategy(price_df, strategy_params)
    if strategy_name == "macd_volume_confirmation":
        return run_macd_volume_confirmation_strategy(price_df, strategy_params)
    if strategy_name == "rsi_adx_filter":
        return run_rsi_adx_filter_strategy(price_df, strategy_params)
    if strategy_name == "rsi_volume_filter":
        return run_rsi_volume_filter_strategy(price_df, strategy_params)
    raise ValueError(f"Unsupported strategy: {strategy_name}")


def add_backtest_columns(df: pd.DataFrame, initial_capital: float) -> pd.DataFrame:
    out = df.copy()
    out["daily_return"] = out["Close"].pct_change().fillna(0)
    out["strategy_return"] = out["position"].shift(1).fillna(0) * out["daily_return"]
    out["strategy_eq"] = initial_capital * (1 + out["strategy_return"]).cumprod()
    out["buyhold_eq"] = initial_capital * (1 + out["daily_return"]).cumprod()
    out["rolling_max"] = out["strategy_eq"].cummax()
    out["drawdown"] = (out["strategy_eq"] - out["rolling_max"]) / out["rolling_max"]
    return out


def build_trade_records(df: pd.DataFrame) -> list:
    trades = []
    in_trade = False
    entry_date = None
    entry_price = None

    for _, row in df.iterrows():
        if not in_trade and not pd.isna(row["buy_marker"]):
            in_trade = True
            entry_date = row["Date"]
            entry_price = float(row["Close"])
        elif in_trade and not pd.isna(row["sell_marker"]):
            exit_price = float(row["Close"])
            trades.append({
                "entry_date": str(entry_date.date()) if hasattr(entry_date, "date") else str(entry_date),
                "entry_price": round(entry_price, 4),
                "exit_date": str(row["Date"].date()) if hasattr(row["Date"], "date") else str(row["Date"]),
                "exit_price": round(exit_price, 4),
                "return_pct": round((exit_price - entry_price) / entry_price * 100, 4),
            })
            in_trade = False
            entry_date = None
            entry_price = None

    return trades


def calculate_metrics(df: pd.DataFrame, trades: list, initial_capital: float) -> dict:
    strategy_eq = df["strategy_eq"]
    strategy_returns = df["strategy_return"].dropna()

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

    max_drawdown = df["drawdown"].min() if "drawdown" in df.columns else np.nan

    winning_trades = [t for t in trades if t["return_pct"] > 0]
    win_rate = len(winning_trades) / len(trades) if trades else np.nan

    return {
        "initial_capital": round(initial_capital, 2),
        "final_equity": round(final_equity, 2),
        "cumulative_return_pct": round(cumulative_return * 100, 2),
        "annualized_return_pct": round(annualized_return * 100, 2) if not pd.isna(annualized_return) else None,
        "annualized_volatility_pct": round(annualized_vol * 100, 2) if not pd.isna(annualized_vol) else None,
        "sharpe_ratio": round(sharpe_ratio, 4) if not pd.isna(sharpe_ratio) else None,
        "max_drawdown_pct": round(max_drawdown * 100, 2) if not pd.isna(max_drawdown) else None,
        "number_of_trades": len(trades),
        "win_rate_pct": round(win_rate * 100, 2) if not pd.isna(win_rate) else None,
    }
