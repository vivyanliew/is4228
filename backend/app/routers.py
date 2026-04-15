import pandas as pd
import pydantic

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
from app.portfolio_backtest import compute_portfolio_metrics, compute_benchmark_metrics
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

        # Compute SPY benchmark metrics
        benchmark_data = {}
        try:
            benchmark_data = compute_benchmark_metrics(
                merged_df, request.initial_capital,
                request.start_date, request.end_date,
            )
        except Exception:
            benchmark_data = {"error": "Could not compute benchmark metrics"}

        return {
            "tickers": normalized_tickers,
            "strategy_name": request.strategy_name,
            "portfolio_metrics": portfolio_metrics,
            "per_ticker_metrics": per_ticker_metrics,
            "per_ticker_signal_rows": per_ticker_signal_rows,
            "portfolio_signal_rows": merged_df.to_dict(orient="records"),
            "benchmark": benchmark_data,
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


@router.post("/backtest/risk-analysis")
def run_risk_analysis(request: PortfolioBacktestRequest):
    """
    Standalone risk analysis for a portfolio backtest.
    Splits the data into in-sample (first 70%) and out-of-sample (last 30%)
    to evaluate overfitting risk using the RiskAgent.
    """
    from app.agents.risk_agent import RiskAgent

    try:
        if not request.tickers:
            raise ValueError("At least one ticker must be provided.")

        normalized_tickers = [t.strip().upper() for t in request.tickers if t.strip()]
        capital_per_ticker = request.initial_capital / len(normalized_tickers)

        merged_df = None
        for ticker in normalized_tickers:
            price_df = fetch_price_data(ticker, request.start_date, request.end_date)
            strategy_df = run_strategy_by_name(
                request.strategy_name, price_df, dict(request.strategy_params),
            )
            result_df, trades, metrics = execute_backtest(strategy_df, capital_per_ticker)
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
        merged_df["portfolio_strategy_eq"] = merged_df[strategy_cols].sum(axis=1)

        # Split 70/30 for IS/OOS
        n = len(merged_df)
        split_idx = int(n * 0.7)

        is_df = merged_df.iloc[:split_idx].copy()
        oos_df = merged_df.iloc[split_idx:].copy()

        is_capital = request.initial_capital
        oos_capital = float(is_df["portfolio_strategy_eq"].iloc[-1])

        is_metrics = compute_portfolio_metrics(is_df, is_capital)
        oos_metrics = compute_portfolio_metrics(oos_df, oos_capital)

        # Estimate trade counts from per-ticker data
        total_is_trades = 0
        total_oos_trades = 0
        for ticker in normalized_tickers:
            price_df = fetch_price_data(ticker, request.start_date, request.end_date)
            strategy_df = run_strategy_by_name(
                request.strategy_name, price_df, dict(request.strategy_params),
            )
            result_df, trades, _ = execute_backtest(strategy_df, capital_per_ticker)
            split_date = result_df.iloc[int(len(result_df) * 0.7)]["Date"]
            for t in trades:
                entry = pd.Timestamp(t["entry_date"])
                if entry < split_date:
                    total_is_trades += 1
                else:
                    total_oos_trades += 1

        is_metrics["number_of_trades"] = total_is_trades
        oos_metrics["number_of_trades"] = total_oos_trades

        risk_agent = RiskAgent()
        risk_result = risk_agent.evaluate({
            "is": {"metrics": is_metrics},
            "oos": {"metrics": oos_metrics},
        })

        # Add context
        risk_result["is_period"] = f"{request.start_date} to 70% mark"
        risk_result["oos_period"] = f"70% mark to {request.end_date}"
        risk_result["is_metrics_summary"] = {
            "sharpe_ratio": is_metrics.get("sharpe_ratio"),
            "cumulative_return_pct": is_metrics.get("cumulative_return_pct"),
            "max_drawdown_pct": is_metrics.get("max_drawdown_pct"),
        }
        risk_result["oos_metrics_summary"] = {
            "sharpe_ratio": oos_metrics.get("sharpe_ratio"),
            "cumulative_return_pct": oos_metrics.get("cumulative_return_pct"),
            "max_drawdown_pct": oos_metrics.get("max_drawdown_pct"),
        }

        return risk_result

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class AIInsightsRequest(pydantic.BaseModel):
    strategy_name: str
    portfolio_metrics: dict
    benchmark: dict = pydantic.Field(default_factory=dict)
    risk_analysis: dict = pydantic.Field(default_factory=dict)
    tickers: list = pydantic.Field(default_factory=list)
    strategy_params: dict = pydantic.Field(default_factory=dict)


@router.post("/backtest/ai-insights")
def generate_ai_insights(request: AIInsightsRequest):
    """Generate AI-powered insights from backtest results using Cohere."""
    import cohere
    import os
    from dotenv import load_dotenv
    from pathlib import Path

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="COHERE_API_KEY not configured")

    co = cohere.Client(api_key)

    pm = request.portfolio_metrics
    bench = request.benchmark
    risk = request.risk_analysis
    tickers_str = ", ".join(request.tickers) if request.tickers else "N/A"
    strategy = request.strategy_name

    # Build strategy params description
    params_str = ", ".join(f"{k}={v}" for k, v in request.strategy_params.items()) if request.strategy_params else "defaults"

    # ── Section A: Performance Insights ──
    perf_prompt = (
        f"You are a quantitative finance analyst. Analyse these backtest results concisely.\n\n"
        f"Strategy: {strategy}\n"
        f"Tickers: {tickers_str}\n"
        f"Parameters: {params_str}\n\n"
        f"Portfolio Metrics:\n"
        f"  Cumulative Return: {pm.get('cumulative_return_pct')}%\n"
        f"  Annualized Return: {pm.get('annualized_return_pct')}%\n"
        f"  Annualized Volatility: {pm.get('annualized_volatility_pct')}%\n"
        f"  Sharpe Ratio: {pm.get('sharpe_ratio')}\n"
        f"  Max Drawdown: {pm.get('max_drawdown_pct')}%\n"
        f"  Final Equity: ${pm.get('final_equity', 0):,.2f} from ${pm.get('initial_capital', 0):,.2f}\n"
    )
    if bench and "alpha_pct" in bench:
        perf_prompt += (
            f"\nBenchmark (SPY):\n"
            f"  Alpha: {bench.get('alpha_pct')}%\n"
            f"  Beta: {bench.get('beta')}\n"
            f"  SPY Cumulative Return: {bench.get('benchmark_cumulative_return_pct')}%\n"
            f"  Sortino Ratio: {bench.get('sortino_ratio')}\n"
        )
    perf_prompt += (
        "\nProvide 3-4 sentences explaining:\n"
        "1) Whether performance is strong/weak and why\n"
        "2) Risk-adjusted performance quality (Sharpe, Sortino context)\n"
        "3) Any notable patterns (high volatility, large drawdown, etc.)\n"
        "Be specific with numbers. Do not use generic statements."
    )

    # ── Section B: Risk Insights ──
    risk_prompt = (
        f"You are a risk analyst. Analyse the risk profile of this {strategy} backtest.\n\n"
        f"Max Drawdown: {pm.get('max_drawdown_pct')}%\n"
        f"Annualized Volatility: {pm.get('annualized_volatility_pct')}%\n"
        f"Sharpe Ratio: {pm.get('sharpe_ratio')}\n"
    )
    if bench and "beta" in bench:
        risk_prompt += f"Beta: {bench.get('beta')}\n"
    if risk:
        risk_prompt += (
            f"\nOverfitting Analysis:\n"
            f"  Score: {risk.get('overfitting_score', 'N/A')}/3 ({risk.get('overfitting_label', 'N/A')})\n"
            f"  Sharpe Decay (OOS/IS): {risk.get('sharpe_decay_ratio', 'N/A')}\n"
            f"  OOS Trade Count: {risk.get('oos_trade_count', 'N/A')}\n"
        )
        flags = risk.get("flags", [])
        if flags:
            risk_prompt += "  Flags: " + "; ".join(flags) + "\n"
    risk_prompt += (
        "\nProvide 2-3 sentences on:\n"
        "1) Drawdown behaviour and what it implies\n"
        "2) Volatility and risk stability\n"
        "3) Whether the strategy is robust or likely overfit\n"
        "Be specific with numbers."
    )

    # ── Section C: Actionable Guidance ──
    action_prompt = (
        f"You are a quantitative trading coach. Based on these results, suggest improvements.\n\n"
        f"Strategy: {strategy}\n"
        f"Parameters: {params_str}\n"
        f"Cumulative Return: {pm.get('cumulative_return_pct')}%\n"
        f"Sharpe Ratio: {pm.get('sharpe_ratio')}\n"
        f"Max Drawdown: {pm.get('max_drawdown_pct')}%\n"
    )
    if risk:
        action_prompt += f"Overfitting Score: {risk.get('overfitting_score', 'N/A')}/3\n"
        action_prompt += f"OOS Trade Count: {risk.get('oos_trade_count', 'N/A')}\n"
    action_prompt += (
        "\nProvide 3-4 bullet points of actionable guidance:\n"
        "- Why performance might be poor (too few trades? parameters too strict?)\n"
        "- Which specific parameters to tweak and in what direction\n"
        "- What to experiment with in the next run\n"
        "Be concrete — reference the actual strategy parameters."
    )

    results = {}
    try:
        perf_resp = co.chat(model="command-a-03-2025", message=perf_prompt)
        results["performance_insights"] = perf_resp.text.strip()
    except Exception as e:
        results["performance_insights"] = f"Could not generate performance insights: {e}"

    try:
        risk_resp = co.chat(model="command-a-03-2025", message=risk_prompt)
        results["risk_insights"] = risk_resp.text.strip()
    except Exception as e:
        results["risk_insights"] = f"Could not generate risk insights: {e}"

    try:
        action_resp = co.chat(model="command-a-03-2025", message=action_prompt)
        results["actionable_guidance"] = action_resp.text.strip()
    except Exception as e:
        results["actionable_guidance"] = f"Could not generate actionable guidance: {e}"

    return results
