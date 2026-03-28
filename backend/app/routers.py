import numpy as np
import pandas as pd
import yfinance as yf

from fastapi import APIRouter, HTTPException

from app.backtest import run_backtest as execute_backtest
from app.models import (
    BacktestRequest,
    BacktestResponse,
    PortfolioBacktestRequest,
    PortfolioBacktestResponse,
)
from app.strategies.strategy_ema import run_strategy as run_ema_strategy
from app.strategies.strategy_macd import run_strategy as run_macd_strategy
from app.strategies.strategy_mean_reversion import run_strategy as run_mean_reversion_strategy
from app.portfolio_backtest import compute_portfolio_metrics

router = APIRouter()


def run_strategy_by_name(strategy_name: str, price_df, strategy_params: dict):
    if strategy_name == "macd":
        return run_macd_strategy(price_df, strategy_params)

    if strategy_name == "mean_reversion":
        return run_mean_reversion_strategy(price_df, strategy_params)

    if strategy_name == "trend_follower":
        return run_ema_strategy(price_df, strategy_params)

    raise ValueError(f"Unsupported strategy: {strategy_name}")



def fetch_price_data(ticker: str, start_date: str, end_date: str):
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



def add_backtest_columns(df: pd.DataFrame, initial_capital: float) -> pd.DataFrame:
    out = df.copy()

    out["daily_return"] = out["Close"].pct_change().fillna(0)

    # Strategy earns return only when already in position from previous day
    out["strategy_return"] = out["position"].shift(1).fillna(0) * out["daily_return"]

    out["strategy_eq"] = initial_capital * (1 + out["strategy_return"]).cumprod()
    out["buyhold_eq"] = initial_capital * (1 + out["daily_return"]).cumprod()

    out["rolling_max"] = out["strategy_eq"].cummax()
    out["drawdown"] = (out["strategy_eq"] - out["rolling_max"]) / out["rolling_max"]

    return out


def build_trade_records(df: pd.DataFrame):
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


def calculate_metrics(df: pd.DataFrame, trades: list, initial_capital: float):
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

@router.post("/backtest/run", response_model=BacktestResponse)
def run_single_backtest(request: BacktestRequest):
    try:
        price_df = fetch_price_data(
            ticker=request.ticker,
            start_date=request.start_date,
            end_date=request.end_date,
        )

        signal_df = run_strategy_by_name(
            strategy_name=request.strategy_name,
            price_df=price_df,
            strategy_params=request.strategy_params.model_dump(),
        )

        signal_df = add_backtest_columns(
            df=signal_df,
            initial_capital=request.initial_capital,
        )

        trades = build_trade_records(signal_df)
        metrics = calculate_metrics(
            df=signal_df,
            trades=trades,
            initial_capital=request.initial_capital,
        )

        signal_rows = signal_df.to_dict(orient="records")

        return BacktestResponse(
            ticker=request.ticker,
            strategy_name=request.strategy_name,
            metrics=metrics,
            trades=trades,
            signal_rows=signal_rows,
        )

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.post("/backtest/run-portfolio", response_model=PortfolioBacktestResponse)
def run_portfolio_backtest(request: PortfolioBacktestRequest):
    try:
        if not request.tickers:
            raise ValueError("At least one ticker must be provided.")

        capital_per_ticker = request.initial_capital / len(request.tickers)

        merged_df = None
        per_ticker_metrics = {}

        for ticker in request.tickers:
            price_df = fetch_price_data(ticker, request.start_date, request.end_date)

            strategy_df = run_strategy_by_name(
                request.strategy_name,
                price_df,
                dict(request.strategy_params),
            )

            result_df, trades, metrics = execute_backtest(strategy_df, capital_per_ticker)
            per_ticker_metrics[ticker] = metrics

            keep_df = result_df[["Date", "strategy_eq", "buyhold_eq"]].copy()
            keep_df = keep_df.rename(columns={
                "strategy_eq": f"strategy_eq_{ticker}",
                "buyhold_eq": f"buyhold_eq_{ticker}",
            })

            if merged_df is None:
                merged_df = keep_df
            else:
                merged_df = pd.merge(merged_df, keep_df, on="Date", how="inner")

        strategy_cols = [c for c in merged_df.columns if c.startswith("strategy_eq_")]
        buyhold_cols = [c for c in merged_df.columns if c.startswith("buyhold_eq_")]

        merged_df["portfolio_strategy_eq"] = merged_df[strategy_cols].sum(axis=1)
        merged_df["portfolio_buyhold_eq"] = merged_df[buyhold_cols].sum(axis=1)

        portfolio_metrics = compute_portfolio_metrics(merged_df, request.initial_capital)

        return {
            "tickers": request.tickers,
            "strategy_name": request.strategy_name,
            "portfolio_metrics": portfolio_metrics,
            "per_ticker_metrics": per_ticker_metrics,
            "portfolio_signal_rows": merged_df.to_dict(orient="records"),
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))