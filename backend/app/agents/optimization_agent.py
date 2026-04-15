import itertools

from app.agents.backtest_agent import BacktestAgent
from app.agents.risk_agent import RiskAgent


class OptimizationAgent:
    """
    Grid-searches a parameter space for a given strategy, ticker, and date range.

    For each candidate parameter set it:
      1. Runs a walk-forward backtest (IS + OOS split) via BacktestAgent
      2. Evaluates overfitting risk via RiskAgent
      3. Scores the candidate on OOS performance
      4. Filters out high-risk or data-thin candidates
      5. Returns the top-N results sorted by score

    Composite score = OOS_Sharpe * (1 + max(Calmar_OOS, 0)) / (1 + |OOS_MaxDD| / 100)

    Candidates are skipped (not included in top-N) if:
      - OOS trade count < 10
      - overfitting_score >= 2
    """

    MIN_OOS_TRADES_OPTIMIZE = 10
    MAX_OVERFITTING_SCORE = 2

    def run(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        strategy_name: str,
        param_grid: dict,
        initial_capital: float = 10000.0,
        is_split: float = 0.7,
        top_n: int = 5,
    ) -> dict:
        param_names = list(param_grid.keys())
        candidates = [
            dict(zip(param_names, combo))
            for combo in itertools.product(*param_grid.values())
        ]

        backtest_agent = BacktestAgent()
        risk_agent = RiskAgent()

        results = []
        skipped = 0
        error_count = 0

        for params in candidates:
            try:
                backtest_result = backtest_agent.run(
                    ticker=ticker,
                    start_date=start_date,
                    end_date=end_date,
                    strategy_name=strategy_name,
                    strategy_params=params,
                    initial_capital=initial_capital,
                    is_split=is_split,
                )
                risk_report = risk_agent.evaluate(backtest_result)

                oos_trade_count = risk_report.get("oos_trade_count", 0)
                overfitting_score = risk_report.get("overfitting_score", 0)

                if oos_trade_count < self.MIN_OOS_TRADES_OPTIMIZE:
                    skipped += 1
                    continue
                if overfitting_score >= self.MAX_OVERFITTING_SCORE:
                    skipped += 1
                    continue

                oos_metrics = backtest_result["oos"]["metrics"]
                oos_sharpe = oos_metrics.get("sharpe_ratio") or 0.0
                oos_max_dd = oos_metrics.get("max_drawdown_pct") or 0.0
                calmar = risk_report.get("calmar_ratio_oos") or 0.0

                score = round(
                    oos_sharpe * (1 + max(calmar, 0)) / (1 + abs(oos_max_dd) / 100),
                    4,
                )

                results.append({
                    "params": params,
                    "is_metrics": backtest_result["is"]["metrics"],
                    "oos_metrics": oos_metrics,
                    "risk_report": risk_report,
                    "score": score,
                })

            except Exception as e:
                error_count += 1

        results.sort(key=lambda x: x["score"], reverse=True)

        return {
            "top_configs": results[:top_n],
            "total_candidates": len(candidates),
            "passed": len(results),
            "skipped": skipped,
            "errors": error_count,
        }
