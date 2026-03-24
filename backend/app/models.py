from pydantic import BaseModel, Field
from typing import List, Dict, Any


class BacktestRequest(BaseModel):
    ticker: str = Field(..., example="AAPL")
    start_date: str = Field(..., example="2015-01-01")
    end_date: str = Field(..., example="2025-01-01")

    initial_capital: float = Field(10000.0, example=10000.0)

    # MACD parameters
    macd_fast: int = Field(12, example=12)
    macd_slow: int = Field(26, example=26)
    macd_signal: int = Field(9, example=9)

    # Bollinger Band parameters
    bb_window: int = Field(20, example=20)
    bb_std: float = Field(2.0, example=2.0)

    # Squeeze settings
    squeeze_quantile_window: int = Field(20, example=20)
    squeeze_threshold_quantile: float = Field(0.2, example=0.2)


class TradeRecord(BaseModel):
    entry_date: str
    entry_price: float
    exit_date: str
    exit_price: float
    return_pct: float


class BacktestResponse(BaseModel):
    ticker: str
    metrics: Dict[str, Any]
    trades: List[TradeRecord]
    signal_rows: List[Dict[str, Any]]