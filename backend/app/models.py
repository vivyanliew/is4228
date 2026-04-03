from typing import Any, Dict, List, Literal, Union

import pydantic

class MacdStrategyParams(pydantic.BaseModel):
    macd_fast: int = pydantic.Field(12, example=12)
    macd_slow: int = pydantic.Field(26, example=26)
    macd_signal: int = pydantic.Field(9, example=9)

    bb_window: int = pydantic.Field(20, example=20)
    bb_std: float = pydantic.Field(2.0, example=2.0)

    squeeze_quantile_window: int = pydantic.Field(20, example=20)
    squeeze_threshold_quantile: float = pydantic.Field(0.2, example=0.2)

class MeanReversionStrategyParams(pydantic.BaseModel):
    bb_window: int = pydantic.Field(20, example=20)
    bb_std: float = pydantic.Field(2.0, example=2.0)
    rsi_window: int = pydantic.Field(14, example=14)
    rsi_entry: float = pydantic.Field(30, example=30)
    rsi_exit: float = pydantic.Field(70, example=70)


class TrendFollowerStrategyParams(pydantic.BaseModel):
    ema_fast: int = pydantic.Field(20, example=20)
    ema_slow: int = pydantic.Field(50, example=50)
    adx_window: int = pydantic.Field(14, example=14)
    adx_threshold: float = pydantic.Field(25.0, example=25.0)

class BacktestRequest(pydantic.BaseModel):
    ticker: str = pydantic.Field(..., example="AAPL")
    start_date: str = pydantic.Field(..., example="2015-01-01")
    end_date: str = pydantic.Field(..., example="2025-01-01")
    initial_capital: float = pydantic.Field(10000.0, example=10000.0)

    strategy_name: Literal["macd", "mean_reversion", "trend_follower"] = pydantic.Field(
        ..., example="trend_follower"
    )
    strategy_params: Union[
        MacdStrategyParams,
        MeanReversionStrategyParams,
        TrendFollowerStrategyParams,
    ]


class TradeRecord(pydantic.BaseModel):
    entry_date: str
    entry_price: float
    exit_date: str
    exit_price: float
    return_pct: float


class BacktestResponse(pydantic.BaseModel):
    ticker: str
    strategy_name: str
    metrics: Dict[str, Any]
    trades: List[TradeRecord]
    signal_rows: List[Dict[str, Any]]

#for portfolio
class PortfolioBacktestRequest(pydantic.BaseModel):
    tickers: List[str] = pydantic.Field(..., example=["AAPL", "MSFT", "NVDA"])
    start_date: str = pydantic.Field(..., example="2015-01-01")
    end_date: str = pydantic.Field(..., example="2025-01-01")
    initial_capital: float = pydantic.Field(10000.0, example=10000.0)

    strategy_name: Literal["macd", "mean_reversion", "trend_follower"] = pydantic.Field(
        ..., example="trend_follower"
    )
    strategy_params: Union[
        MacdStrategyParams,
        MeanReversionStrategyParams,
        TrendFollowerStrategyParams,
    ]


class PortfolioBacktestResponse(pydantic.BaseModel):
    tickers: List[str]
    strategy_name: str
    portfolio_metrics: Dict[str, Any]
    per_ticker_metrics: Dict[str, Dict[str, Any]]
    per_ticker_signal_rows: Dict[str, List[Dict[str, Any]]]
    portfolio_signal_rows: List[Dict[str, Any]]
