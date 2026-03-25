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


class BacktestRequest(pydantic.BaseModel):
    ticker: str = pydantic.Field(..., example="AAPL")
    start_date: str = pydantic.Field(..., example="2015-01-01")
    end_date: str = pydantic.Field(..., example="2025-01-01")
    initial_capital: float = pydantic.Field(10000.0, example=10000.0)

    strategy_name: Literal["macd", "mean_reversion"] = pydantic.Field(..., example="mean_reversion")
    strategy_params: Union[MacdStrategyParams, MeanReversionStrategyParams]


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