from fastapi import FastAPI, HTTPException

from app.models import BacktestRequest, BacktestResponse
from app.data import load_data
from app.strategy_macd import add_indicators, generate_signals
from app.backtest import run_backtest

app = FastAPI(title="Backtesting API")


@app.get("/")
def root():
    return {"message": "Backend is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/backtest/macd-breakout", response_model=BacktestResponse)
def backtest_macd_breakout(request: BacktestRequest):
    try:
        df = load_data(
            ticker=request.ticker,
            start_date=request.start_date,
            end_date=request.end_date,
        )

        df = add_indicators(
            df=df,
            macd_fast=request.macd_fast,
            macd_slow=request.macd_slow,
            macd_signal=request.macd_signal,
            bb_window=request.bb_window,
            bb_std=request.bb_std,
            squeeze_quantile_window=request.squeeze_quantile_window,
            squeeze_threshold_quantile=request.squeeze_threshold_quantile,
        )

        df = generate_signals(df)

        result_df, trades, metrics = run_backtest(
            df=df,
            initial_capital=request.initial_capital,
        )

        signal_columns = [
            "Date",
            "Close",
            "macd_line",
            "macd_signal",
            "macd_hist",
            "bb_mid",
            "bb_upper",
            "bb_lower",
            "bb_width",
            "bb_width_threshold",
            "is_squeeze",
            "buy_signal",
            "sell_signal",
            "position",
            "buy_marker",
            "sell_marker",
            "buyhold_eq",
            "strategy_eq",
            "drawdown",
        ]

        signal_rows_df = result_df[signal_columns].copy()
        signal_rows_df["Date"] = signal_rows_df["Date"].astype(str)

        return {
            "ticker": request.ticker,
            "metrics": metrics,
            "trades": trades,
            "signal_rows": signal_rows_df.to_dict(orient="records"),
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))