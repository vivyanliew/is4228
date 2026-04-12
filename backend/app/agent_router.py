from fastapi import APIRouter, HTTPException

from app.agents.backtest_agent import BacktestAgent
from app.agents.risk_agent import RiskAgent
from app.agents.optimization_agent import OptimizationAgent
from app.agents.market_context_agent import MarketContextAgent
from app.models import (
    AgentBacktestRequest,
    AgentBacktestResponse,
    OptimizeRequest,
    OptimizeResponse,
    MarketContextRequest,
    MarketContextResponse,
)

agent_router = APIRouter(prefix="/agent", tags=["agents"])


@agent_router.post("/backtest", response_model=AgentBacktestResponse)
def agent_walkforward_backtest(request: AgentBacktestRequest):
    """
    Walk-forward backtest for a single ticker and strategy.
    Splits historical data into in-sample (IS) and out-of-sample (OOS) windows,
    runs the backtest on both, and returns a risk report flagging overfitting signals.
    """
    try:
        result = BacktestAgent().run(
            ticker=request.ticker,
            start_date=request.start_date,
            end_date=request.end_date,
            strategy_name=request.strategy_name,
            strategy_params=request.strategy_params,
            initial_capital=request.initial_capital,
            is_split=request.is_split,
        )
        risk_report = RiskAgent().evaluate(result)

        return AgentBacktestResponse(
            is_metrics=result["is"]["metrics"],
            oos_metrics=result["oos"]["metrics"],
            is_trades=result["is"]["trades"],
            oos_trades=result["oos"]["trades"],
            is_end_date=result["is_end_date"],
            oos_start_date=result["oos_start_date"],
            risk_report=risk_report,
        )

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@agent_router.post("/optimize", response_model=OptimizeResponse)
def agent_optimize(request: OptimizeRequest):
    """
    Grid-search optimizer.  Accepts a param_grid (dict of param -> list of values),
    runs a walk-forward backtest for every candidate in the Cartesian product,
    filters out statistically weak or high-overfitting-risk configs,
    and returns the top-5 by composite OOS score.

    Warning: large grids can take tens of seconds. Keep each axis to 2-4 values
    for interactive use.
    """
    try:
        result = OptimizationAgent().run(
            ticker=request.ticker,
            start_date=request.start_date,
            end_date=request.end_date,
            strategy_name=request.strategy_name,
            param_grid=request.param_grid,
            initial_capital=request.initial_capital,
            is_split=request.is_split,
        )
        return OptimizeResponse(**result)

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@agent_router.post("/market-context", response_model=MarketContextResponse)
def agent_market_context(request: MarketContextRequest):
    """
    Computes market regime context for a ticker over a date range.
    Returns regime classification, volatility, SPY correlation,
    and a recommended strategy bias for strategy generation.
    """
    try:
        result = MarketContextAgent().run(
            ticker=request.ticker,
            start_date=request.start_date,
            end_date=request.end_date,
        )
        return MarketContextResponse(**result)

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))