import numpy as np
import pandas as pd


def run_backtest(df: pd.DataFrame, initial_capital: float = 10000.0):
    out = df.copy()

    # Daily returns of the asset
    out["asset_return"] = out["Close"].pct_change().fillna(0.0)

    # Strategy return uses yesterday's position
    out["strategy_return"] = out["position"].shift(1).fillna(0.0) * out["asset_return"]

    # Equity curves
    out["buyhold_eq"] = initial_capital * (1 + out["asset_return"]).cumprod()
    out["strategy_eq"] = initial_capital * (1 + out["strategy_return"]).cumprod()

    # Drawdown
    out["strategy_peak"] = out["strategy_eq"].cummax()
    out["drawdown"] = out["strategy_eq"] / out["strategy_peak"] - 1.0

    trades = extract_trades(out)
    metrics = compute_metrics(out, trades, initial_capital)

    return out, trades, metrics


def extract_trades(df: pd.DataFrame):
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
            exit_date = row["Date"]
            exit_price = float(row["Close"])

            trade_return = (exit_price - entry_price) / entry_price

            trades.append({
                "entry_date": str(entry_date.date()) if hasattr(entry_date, "date") else str(entry_date),
                "entry_price": round(entry_price, 4),
                "exit_date": str(exit_date.date()) if hasattr(exit_date, "date") else str(exit_date),
                "exit_price": round(exit_price, 4),
                "return_pct": round(trade_return * 100, 4),
            })

            in_trade = False
            entry_date = None
            entry_price = None

    return trades


def compute_metrics(df: pd.DataFrame, trades: list, initial_capital: float):
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

    metrics = {
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

    return metrics