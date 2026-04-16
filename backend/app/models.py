from typing import Any, Dict, List, Literal, Optional, Tuple, Union

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
    benchmark: Optional[Dict[str, Any]] = None


class StrategyGenerationRequest(pydantic.BaseModel):
    ticker: str = pydantic.Field(..., example="BTC-USD")
    start_date: str = pydantic.Field(..., example="2022-01-01")
    end_date: str = pydantic.Field(..., example="2024-12-31")
    market_context: Dict[str, Any] = pydantic.Field(default_factory=dict)
    max_candidates: int = pydantic.Field(3, ge=1, le=10)
    use_llm: bool = pydantic.Field(True)
    allow_experimental: bool = pydantic.Field(True)


class StrategySpecResponse(pydantic.BaseModel):
    strategy_name: str
    strategy_params: Dict[str, Any]
    description: str
    rationale: Optional[str] = None
    source: str
    backtestable: bool
    confidence: float
    research_basis: List[str] = pydantic.Field(default_factory=list)
    generated_code: Optional[str] = None
    implementation_hint: Optional[str] = None
    metadata: Dict[str, Any] = pydantic.Field(default_factory=dict)


class StrategyGenerationResponse(pydantic.BaseModel):
    ticker: str
    start_date: str
    end_date: str
    market_context: Dict[str, Any]
    strategies: List[StrategySpecResponse]


class StrategyGenerationRequest(pydantic.BaseModel):
    ticker: str = pydantic.Field(..., example="BTC-USD")
    start_date: str = pydantic.Field(..., example="2022-01-01")
    end_date: str = pydantic.Field(..., example="2024-12-31")
    market_context: Dict[str, Any] = pydantic.Field(default_factory=dict)
    max_candidates: int = pydantic.Field(3, ge=1, le=10)
    use_llm: bool = pydantic.Field(True)
    allow_experimental: bool = pydantic.Field(True)


class StrategySpecResponse(pydantic.BaseModel):
    strategy_name: str
    strategy_params: Dict[str, Any]
    description: str
    rationale: Optional[str] = None
    source: str
    backtestable: bool
    confidence: float
    research_basis: List[str] = pydantic.Field(default_factory=list)
    generated_code: Optional[str] = None
    implementation_hint: Optional[str] = None
    metadata: Dict[str, Any] = pydantic.Field(default_factory=dict)


class StrategyGenerationResponse(pydantic.BaseModel):
    ticker: str
    start_date: str
    end_date: str
    market_context: Dict[str, Any]
    strategies: List[StrategySpecResponse]


# ---------------------------------------------------------------------------
# Agent models
# ---------------------------------------------------------------------------

class AgentBacktestRequest(pydantic.BaseModel):
    ticker: str = pydantic.Field(..., example="AAPL")
    start_date: str = pydantic.Field(..., example="2015-01-01")
    end_date: str = pydantic.Field(..., example="2025-01-01")
    initial_capital: float = pydantic.Field(10000.0, example=10000.0)
    strategy_name: str = pydantic.Field(..., example="mean_reversion")
    strategy_params: Dict[str, Any] = pydantic.Field(
        ..., example={"bb_window": 20, "bb_std": 2.0, "rsi_window": 14, "rsi_entry": 30, "rsi_exit": 70}
    )
    is_split: float = pydantic.Field(0.7, example=0.7, ge=0.3, le=0.9)


class AgentBacktestResponse(pydantic.BaseModel):
    is_metrics: Dict[str, Any]
    oos_metrics: Dict[str, Any]
    is_trades: List[Dict[str, Any]]
    oos_trades: List[Dict[str, Any]]
    is_end_date: str
    oos_start_date: str
    risk_report: Dict[str, Any]


class OptimizeRequest(pydantic.BaseModel):
    ticker: str = pydantic.Field(..., example="AAPL")
    start_date: str = pydantic.Field(..., example="2015-01-01")
    end_date: str = pydantic.Field(..., example="2025-01-01")
    initial_capital: float = pydantic.Field(10000.0, example=10000.0)
    strategy_name: str = pydantic.Field(..., example="mean_reversion")
    param_grid: Dict[str, List[Any]] = pydantic.Field(
        ...,
        example={
            "bb_window": [15, 20, 25],
            "bb_std": [1.5, 2.0, 2.5],
            "rsi_window": [14],
            "rsi_entry": [25, 30],
            "rsi_exit": [70, 75],
        },
    )
    is_split: float = pydantic.Field(0.7, example=0.7, ge=0.3, le=0.9)


class OptimizeResponse(pydantic.BaseModel):
    top_configs: List[Dict[str, Any]]
    total_candidates: int
    passed: int
    skipped: int
    errors: int
    fallback_used: bool = False
    fallback_reason: Optional[str] = None

class MarketContextRequest(pydantic.BaseModel):
    ticker: str = pydantic.Field(..., example="BTC-USD")
    start_date: str = pydantic.Field(..., example="2022-01-01")
    end_date: str = pydantic.Field(..., example="2024-12-31")


class MarketContextResponse(pydantic.BaseModel):
    ticker: str
    start_date: str
    end_date: str
    regime: Literal["trending", "ranging"]
    trend_direction: Literal["up", "down", "sideways"]
    sma_200_slope: float
    realized_vol_30d: float
    correlation_to_spy: float
    strategy_bias: Literal["momentum", "mean_reversion", "neutral"]
    reasoning: str


class ReportRequest(pydantic.BaseModel):
    ticker: str = pydantic.Field(..., example="BTC-USD")
    start_date: str = pydantic.Field(..., example="2022-01-01")
    end_date: str = pydantic.Field(..., example="2024-12-31")
    market_context: Dict[str, Any] = pydantic.Field(
        ...,
        description="MarketContextAgent output"
    )
    strategy_specs: List[Dict[str, Any]] = pydantic.Field(
        ...,
        description="List of StrategySpec dicts from StrategyGenerationAgent"
    )
    backtest_results: Dict[str, Any] = pydantic.Field(
        ...,
        description="BacktestAgent output: is_metrics, oos_metrics, split_date, trade lists"
    )
    risk_results: Dict[str, Any] = pydantic.Field(
        ...,
        description="RiskAgent output: overfitting_score, overfitting_label, calmar_ratio_oos, flags"
    )
    optimization_results: List[Dict[str, Any]] = pydantic.Field(
        ...,
        description="OptimizationAgent top-N configs, sorted best-first"
    )

class ReportResponse(pydantic.BaseModel):
    ticker: str
    start_date: str
    end_date: str
    markdown: str                       # full synthesised report
    summary: str                        # executive summary paragraph only
    warnings: list[str]                 # ⚠️ bullets extracted from Risk Warnings section
    sections: dict[str, str]            # keyed sub-sections for Streamlit expanders
    # Expected keys:
    #   "Market Context", "Strategy Overview", "Backtest Performance",
    #   "Risk Analysis", "Parameter Recommendations", "Risk Warnings", "Conclusion"
    synthesis_source: Literal["cohere", "rule_based"]
    # Tells the caller whether the LLM was used or the fallback fired
