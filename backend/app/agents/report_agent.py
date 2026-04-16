from __future__ import annotations
import os
from pathlib import Path
from typing import Optional
import cohere
from dotenv import load_dotenv
from app.models import ReportRequest
from app.utils_report import (
    build_user_prompt, 
    call_cohere,
    extract_sections, 
    extract_summary, 
    extract_warnings,
    rule_based_report
    )

class ReportAgent:
    """
    Synthesizes outputs from the market, strategy, backtest, risk, and
    optimization agents into a research report.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        self.api_key = os.getenv("COHERE_API_KEY") if api_key is None else api_key

    def run(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        market_context: dict,
        strategy_specs: list[dict],
        backtest_results: dict,
        risk_results: dict,
        optimization_results: list[dict],
    ) -> dict:

        # Try Cohere synthesis 
        if self.api_key:
            try:
                user_prompt = build_user_prompt(
                    ticker, start_date, end_date, market_context,
                    strategy_specs, backtest_results,
                    risk_results, optimization_results,
                )
                markdown = call_cohere(user_prompt, api_key = self.api_key)
            except Exception as exc:
                markdown = (
                    rule_based_report(
                        ticker, start_date, end_date, market_context,
                        strategy_specs, backtest_results, risk_results, optimization_results,
                    )
                    + f"\n\n> ⚠️ Cohere synthesis failed ({exc}); rule-based report shown."
                )
        else:
            # No API key — use rule-based fallback
            markdown = rule_based_report(
                ticker, start_date, end_date, market_context,
                strategy_specs, backtest_results, risk_results, optimization_results,
            )
    
        # Post-processing: extract sections, summary, and warnings from the markdown
        sections = extract_sections(markdown=markdown)
        summary = extract_summary(sections=sections)
        warnings = extract_warnings(sections=sections)
    
        return {
            "ticker": ticker,
            "start_date": start_date,
            "end_date": end_date,
            "markdown": markdown,
            "summary": summary,
            "warnings": warnings,
            "sections": sections,
            "synthesis_source": "cohere" if self.api_key else "rule_based",
        }
