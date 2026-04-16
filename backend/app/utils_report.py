from __future__ import annotations
import os
import json
import textwrap
from datetime import datetime
from typing import Any
from dotenv import load_dotenv
from pathlib import Path
import cohere
from app.market_intel import COHERE_API_KEY

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

api_key = os.getenv("COHERE_API_KEY")

# ---------------------------------------------------------------------------
# Helper – safe JSON serialisation (numpy floats, NaNs, etc.)
# ---------------------------------------------------------------------------
 
def safe_json(obj: Any, indent: int = 2) -> str:
    def _default(o):
        try:
            return float(o)
        except (TypeError, ValueError):
            return str(o)
 
    return json.dumps(obj, indent=indent, default=_default)
 
 
# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def build_user_prompt(
    ticker: str,
    start_date: str,
    end_date: str,
    market_context: dict,
    strategy_specs: list[dict],
    backtest_results: dict,
    risk_results: dict,
    optimization_results: list[dict],
) -> str:
    
    start = start_date
    end = end_date

    # Truncate optimization_results to top-3 to save tokens
    top_opts = optimization_results[:3] if optimization_results else []
 
    prompt = textwrap.dedent(f"""
        Write a full quantitative strategy research report for **{ticker}**
        covering the period **{start}** to **{end}**.
 
        Use ONLY the data below. Do not invent numbers.
 
        ---
        ## 1. MARKET CONTEXT
        {safe_json(market_context)}
 
        ---
        ## 2. STRATEGY SPECIFICATIONS TESTED
        {safe_json(strategy_specs)}
 
        ---
        ## 3. BACKTEST RESULTS (In-Sample vs Out-of-Sample)
        {safe_json(backtest_results)}
 
        ---
        ## 4. RISK ANALYSIS
        {safe_json(risk_results)}
 
        ---
        ## 5. TOP OPTIMISED PARAMETER SETS
        {safe_json(top_opts)}
 
        ---
        Structure your report with these exact top-level sections:
        1. Executive Summary
        2. Market Context & Regime Analysis
        3. Strategy Overview
        4. Backtest Performance (IS vs OOS comparison table)
        5. Risk Analysis & Overfitting Assessment
        6. Parameter Recommendations
        7. Risk Warnings & Caveats
        8. Conclusion
 
        For section 4, include a Markdown table comparing IS Sharpe, OOS Sharpe,
        Max Drawdown, Win Rate, and Total Return for each strategy tested.
        For section 5, call out the overfitting score and Calmar ratio explicitly.
        For section 7, list each warning as a bullet point starting with ⚠️.
    """).strip()
 
    return prompt
 
 
# ---------------------------------------------------------------------------
# Cohere call
# ---------------------------------------------------------------------------
 
def call_cohere(user_prompt: str, api_key: str) -> str:
    client = cohere.Client(api_key)

    system_prompt = """
        You are a quantitative research analyst writing a professional strategy
        research report. Your output must be structured, precise, and actionable.
        Use Markdown with clear headings. Avoid generic filler text.
        When citing numbers, round to 2–4 decimal places.
        Flag any statistical or overfitting concerns explicitly.
        """

    response = client.chat(
        model="command-a-03-2025",
        preamble=system_prompt,
        message=user_prompt,
        temperature=0.3,          # low temperature → factual, consistent
        max_tokens=4096,
    )
    return response.text
 
 
# ---------------------------------------------------------------------------
# Post-processing helpers
# ---------------------------------------------------------------------------
 
def extract_sections(markdown: str) -> dict[str, str]:
    """
    Split the LLM markdown into keyed sections so Streamlit can render
    each one as an independent expandable panel.
    """
    import re
 
    section_keys = [
        "Executive Summary",
        "Market Context",
        "Strategy Overview",
        "Backtest Performance",
        "Risk Analysis",
        "Parameter Recommendations",
        "Risk Warnings",
        "Conclusion",
    ]
 
    # Find all H2/H3 headings and their positions
    pattern = re.compile(r"^#{1,3}\s+(.+)$", re.MULTILINE)
    matches = list(pattern.finditer(markdown))
 
    sections: dict[str, str] = {}
    for i, match in enumerate(matches):
        heading = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        content = markdown[start:end].strip()
 
        # Map to canonical key
        for key in section_keys:
            if key.lower() in heading.lower():
                sections[key] = f"### {heading}\n\n{content}"
                break
        else:
            sections[heading] = f"### {heading}\n\n{content}"
 
    return sections
 
 
def extract_summary(sections: dict[str, str]) -> str:
    return sections.get("Executive Summary", "").replace("### Executive Summary", "").strip()
 
 
def extract_warnings(sections: dict[str, str]) -> list[str]:
    import re
 
    warnings_text = sections.get("Risk Warnings", "")
    # Pull out bullet lines that start with ⚠️ or -
    bullets = re.findall(r"(?:⚠️|[-*])\s+(.+)", warnings_text)
    return [b.strip() for b in bullets if b.strip()]
 
 
# ---------------------------------------------------------------------------
# Fallback: rule-based report (if Cohere is unavailable)
# ---------------------------------------------------------------------------
 
def rule_based_report(
    ticker: str,
    start_date: str,
    end_date: str,
    market_context: dict,
    backtest_results: dict,
    risk_results: dict,
    optimization_results: list[dict],
) -> str:

    start = start_date
    end = end_date
    regime = market_context.get("regime", "unknown")
    bias = market_context.get("strategy_bias", "neutral")
    vol = market_context.get("realized_vol_30d", float("nan"))
 
    is_metrics = backtest_results.get("is_metrics", {})
    oos_metrics = backtest_results.get("oos_metrics", {})
    overfit_label = risk_results.get("overfitting_label", "Unknown")
    overfit_score = risk_results.get("overfitting_score", "N/A")
    calmar = risk_results.get("calmar_ratio_oos", float("nan"))
 
    top = optimization_results[0] if optimization_results else {}
 
    warnings = []
    if risk_results.get("overfitting_score", 0) >= 2:
        warnings.append("⚠️ High overfitting risk — validate on additional OOS windows before live deployment.")
    if oos_metrics.get("total_return", 0) < 0:
        warnings.append("⚠️ Strategy produced negative returns on the OOS window.")
    if oos_metrics.get("num_trades", 0) < 20:
        warnings.append("⚠️ Fewer than 20 OOS trades — results may not be statistically significant.")
 
    warning_md = "\n".join(f"- {w}" for w in warnings) if warnings else "- No major warnings."
 
    return textwrap.dedent(f"""
        # Strategy Research Report — {ticker}
        *Period: {start} → {end} | Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*
 
        ---
 
        ## 1. Executive Summary
        Analysis of **{ticker}** identified a **{regime}** market regime with a
        **{bias}** strategy bias. The best-performing configuration achieved an
        OOS Sharpe of **{oos_metrics.get('sharpe_ratio', 'N/A')}** and a Calmar
        ratio of **{calmar:.2f}** with an overfitting risk assessed as **{overfit_label}**.
 
        ---
 
        ## 2. Market Context & Regime Analysis
        | Metric | Value |
        |---|---|
        | Regime | {regime} |
        | Trend Direction | {market_context.get('trend_direction', 'N/A')} |
        | 30-Day Realised Vol | {vol:.1%} |
        | SPY Correlation | {market_context.get('correlation_spy', 'N/A')} |
        | Strategy Bias | {bias} |
 
        **Reasoning:** {market_context.get('reasoning', 'N/A')}
 
        ---
 
        ## 3. Strategy Overview
        Strategies were selected based on the **{bias}** bias derived from regime detection.
 
        ---
 
        ## 4. Backtest Performance (IS vs OOS)
        | Metric | In-Sample | Out-of-Sample |
        |---|---|---|
        | Sharpe Ratio | {is_metrics.get('sharpe_ratio', 'N/A')} | {oos_metrics.get('sharpe_ratio', 'N/A')} |
        | Max Drawdown | {is_metrics.get('max_drawdown', 'N/A')} | {oos_metrics.get('max_drawdown', 'N/A')} |
        | Win Rate | {is_metrics.get('win_rate', 'N/A')} | {oos_metrics.get('win_rate', 'N/A')} |
        | Total Return | {is_metrics.get('total_return', 'N/A')} | {oos_metrics.get('total_return', 'N/A')} |
        | Num Trades | {is_metrics.get('num_trades', 'N/A')} | {oos_metrics.get('num_trades', 'N/A')} |
 
        ---
 
        ## 5. Risk Analysis & Overfitting Assessment
        | Check | Value |
        |---|---|
        | Overfitting Score | {overfit_score} / 3 |
        | Overfitting Label | {overfit_label} |
        | Calmar Ratio (OOS) | {calmar:.2f} |
 
        ---
 
        ## 6. Parameter Recommendations
        Best configuration found:
        ```json
        {safe_json(top.get('params', top))}
        ```
        Composite score: **{top.get('composite_score', 'N/A')}**
 
        ---
 
        ## 7. Risk Warnings & Caveats
        {warning_md}
        - ⚠️ Past performance does not guarantee future results.
        - ⚠️ This report is for research purposes only and does not constitute financial advice.
 
        ---
 
        ## 8. Conclusion
        Based on the analysis, the strategy shows **{overfit_label.lower()}** overfitting risk
        with a **{bias}**-oriented setup suited to the current **{regime}** regime.
        {'Further validation is strongly recommended before live deployment.' if overfit_score != 'N/A' and int(overfit_score) >= 2 else 'The strategy may be suitable for paper trading with continued monitoring.'}
    """).strip()