import pandas as pd

from fastapi import APIRouter, HTTPException

from app.backtest import run_backtest as execute_backtest
from app.models import (
    BacktestRequest,
    BacktestResponse,
    PortfolioBacktestRequest,
    PortfolioBacktestResponse,
    StrategyGenerationRequest,
    StrategyGenerationResponse,
)
from app.agents.strategy_generation_agent import StrategyGenerationAgent
from app.strategies.strategy_macd import run_strategy_multi_ticker as run_macd_multi_strategy
from app.portfolio_backtest import compute_portfolio_metrics
from app.market_intel import get_market_intel
from app.utils import (
    fetch_price_data,
    run_strategy_by_name,
    add_backtest_columns,
    build_trade_records,
    calculate_metrics,
)

router = APIRouter()
strategy_generation_agent = StrategyGenerationAgent()


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

        normalized_tickers = [ticker.strip().upper() for ticker in request.tickers if ticker.strip()]
        if not normalized_tickers:
            raise ValueError("At least one valid ticker must be provided.")

        capital_per_ticker = request.initial_capital / len(normalized_tickers)

        merged_df = None
        per_ticker_metrics = {}
        per_ticker_signal_rows = {}

        for ticker in normalized_tickers:
            price_df = fetch_price_data(ticker, request.start_date, request.end_date)

            strategy_df = run_strategy_by_name(
                request.strategy_name,
                price_df,
                dict(request.strategy_params),
            )

            result_df, trades, metrics = execute_backtest(strategy_df, capital_per_ticker)
            per_ticker_metrics[ticker] = metrics
            per_ticker_signal_rows[ticker] = result_df.to_dict(orient="records")

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
            "tickers": normalized_tickers,
            "strategy_name": request.strategy_name,
            "portfolio_metrics": portfolio_metrics,
            "per_ticker_metrics": per_ticker_metrics,
            "per_ticker_signal_rows": per_ticker_signal_rows,
            "portfolio_signal_rows": merged_df.to_dict(orient="records"),
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/backtest/run-macd-multi", response_model=BacktestResponse)
def run_macd_multi_backtest(request: PortfolioBacktestRequest):
    """
    Run MACD strategy on multiple tickers with equal weighting within the strategy.
    """
    try:
        if not request.tickers:
            raise ValueError("At least one ticker must be provided.")
        
        # Fetch price data for all tickers
        price_dfs = {}
        for ticker in request.tickers:
            price_dfs[ticker] = fetch_price_data(ticker, request.start_date, request.end_date)
        
        # Run multi-ticker MACD strategy
        signal_df = run_macd_multi_strategy(
            price_dfs=price_dfs,
            params=dict(request.strategy_params),
        )
        
        # Add backtest columns and calculate metrics
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
            ticker=",".join(request.tickers),
            strategy_name=f"{request.strategy_name}_multi",
            metrics=metrics,
            trades=trades,
            signal_rows=signal_rows,
        )
    
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    


@router.get("/market-intel/{ticker}")
def get_market_intel_endpoint(ticker: str):
    try:
        return get_market_intel(ticker)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error fetching data for {ticker}: {str(e)}"
        )


@router.post("/strategy-generation/run", response_model=StrategyGenerationResponse)
def run_strategy_generation(request: StrategyGenerationRequest):
    try:
        specs = strategy_generation_agent.generate(
            ticker=request.ticker,
            start_date=request.start_date,
            end_date=request.end_date,
            market_context=request.market_context,
            max_candidates=request.max_candidates,
            use_llm=request.use_llm,
            allow_experimental=request.allow_experimental,
        )

        return StrategyGenerationResponse(
            ticker=request.ticker,
            start_date=request.start_date,
            end_date=request.end_date,
            market_context=request.market_context,
            strategies=[
                {
                    "strategy_name": spec.strategy_name,
                    "strategy_params": spec.strategy_params,
                    "description": spec.description,
                    "rationale": spec.rationale,
                    "source": spec.source,
                    "backtestable": spec.backtestable,
                    "confidence": spec.confidence,
                    "research_basis": spec.research_basis,
                    "generated_code": spec.generated_code,
                    "implementation_hint": spec.implementation_hint,
                    "metadata": spec.metadata,
                }
                for spec in specs
            ],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
