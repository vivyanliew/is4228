from concurrent.futures import Future, ThreadPoolExecutor
import re
import time

import pandas as pd
import requests
import streamlit as st

from api import (
    AGENT_BACKTEST_URL,
    AGENT_MARKET_CONTEXT_URL,
    AGENT_OPTIMIZE_URL,
    AGENT_REPORT_URL,
    AI_INSIGHTS_URL,
    MARKET_INTEL_URL,
    RISK_ANALYSIS_URL,
    STRATEGY_GENERATION_URL,
    build_payload,
    get_backtest_endpoint,
)
from charts import render_charts_breakout, render_charts_mean_reversion, render_charts_trend, render_risk_analysis, render_ai_insights
from metrics import render_metrics_breakout, render_metrics_mean_reversion, render_metrics_trend
from sidebar import ASSETS, STRATEGIES

st.set_page_config(page_title="Strategy Lab", layout="wide")

DEFAULT_BACKTEST_START = pd.to_datetime("2018-01-01")
DEFAULT_BACKTEST_END = pd.to_datetime("2025-12-31")
DEFAULT_GENERATION_START = pd.to_datetime("2018-01-01")
DEFAULT_GENERATION_END = pd.to_datetime("2025-12-31")
BACKGROUND_EXECUTOR = ThreadPoolExecutor(max_workers=4)

TIER_RANK = {
    "Free": 1,
    "Pro": 2,
    "Advanced": 3,
}

TIER_COPY = {
    "Free": "Backtester access with the three core strategies and optional portfolio runs.",
    "Pro": "Adds Market Intelligence on top of the backtester.",
    "Advanced": "Unlocks the full workflow, including Strategy Generation.",
}

if "backtest_data" not in st.session_state:
    st.session_state["backtest_data"] = None
if "backtest_strategy" not in st.session_state:
    st.session_state["backtest_strategy"] = None
if "market_intel_result" not in st.session_state:
    st.session_state["market_intel_result"] = None
if "strategy_generation_result" not in st.session_state:
    st.session_state["strategy_generation_result"] = None
if "strategy_generation_market_context" not in st.session_state:
    st.session_state["strategy_generation_market_context"] = None
if "strategy_generated_backtest_result" not in st.session_state:
    st.session_state["strategy_generated_backtest_result"] = None
if "strategy_generated_optimization_result" not in st.session_state:
    st.session_state["strategy_generated_optimization_result"] = None
if "strategy_generated_report_result" not in st.session_state:
    st.session_state["strategy_generated_report_result"] = None
if "strategy_generated_all_evaluations" not in st.session_state:
    st.session_state["strategy_generated_all_evaluations"] = {}
if "strategy_generated_background_futures" not in st.session_state:
    st.session_state["strategy_generated_background_futures"] = {}
if "strategy_generated_report_future" not in st.session_state:
    st.session_state["strategy_generated_report_future"] = None
if "selected_tier" not in st.session_state:
    st.session_state["selected_tier"] = "Free"
if "backtest_mode" not in st.session_state:
    st.session_state["backtest_mode"] = "Single Asset"
if "backtest_portfolio_assets" not in st.session_state:
    st.session_state["backtest_portfolio_assets"] = ["AAPL", "MSFT"]
if "backtest_config" not in st.session_state:
    st.session_state["backtest_config"] = {}
if "risk_analysis_data" not in st.session_state:
    st.session_state["risk_analysis_data"] = None
if "ai_insights_data" not in st.session_state:
    st.session_state["ai_insights_data"] = None
if "backtest_single_asset_value" not in st.session_state:
    st.session_state["backtest_single_asset_value"] = ASSETS[0]
if "market_intel_signature" not in st.session_state:
    st.session_state["market_intel_signature"] = None
if "backtest_signature" not in st.session_state:
    st.session_state["backtest_signature"] = None
if "strategy_generation_signature" not in st.session_state:
    st.session_state["strategy_generation_signature"] = None
if "strategy_generation_cache" not in st.session_state:
    st.session_state["strategy_generation_cache"] = {}
if "selected_generated_strategy_signature" not in st.session_state:
    st.session_state["selected_generated_strategy_signature"] = None


def tier_enabled(active_tier: str, required_tier: str) -> bool:
    return TIER_RANK[active_tier] >= TIER_RANK[required_tier]


def clear_market_intelligence_results() -> None:
    st.session_state["market_intel_result"] = None


def clear_backtest_results() -> None:
    st.session_state["backtest_data"] = None
    st.session_state["backtest_strategy"] = None
    st.session_state["backtest_config"] = {}
    st.session_state["risk_analysis_data"] = None
    st.session_state["ai_insights_data"] = None


def clear_strategy_generation_results() -> None:
    st.session_state["strategy_generation_result"] = None
    st.session_state["strategy_generation_market_context"] = None
    st.session_state["strategy_generated_backtest_result"] = None
    st.session_state["strategy_generated_optimization_result"] = None
    st.session_state["strategy_generated_report_result"] = None
    st.session_state["strategy_generated_all_evaluations"] = {}
    st.session_state["strategy_generated_background_futures"] = {}
    st.session_state["strategy_generated_report_future"] = None


def reset_strategy_generation_downstream_results() -> None:
    st.session_state["strategy_generated_backtest_result"] = None
    st.session_state["strategy_generated_optimization_result"] = None
    st.session_state["strategy_generated_report_result"] = None
    st.session_state["strategy_generated_all_evaluations"] = {}
    st.session_state["strategy_generated_background_futures"] = {}
    st.session_state["strategy_generated_report_future"] = None


def run_demo_loading_step(message: str, seconds: float = 3.0) -> None:
    with st.spinner(message):
        time.sleep(seconds)


def extract_error_message(response: requests.Response | None = None, exc: Exception | None = None) -> str:
    if exc is not None:
        message = str(exc)
        if "Read timed out" in message:
            return "The request is taking longer than expected. Please try again in a moment."
        if "Failed to establish a new connection" in message or "Connection refused" in message:
            return "The backend service is not reachable right now. Please make sure the API server is running."
        return "Something went wrong while contacting the backend. Please try again."

    if response is not None:
        try:
            payload = response.json()
            if isinstance(payload, dict):
                detail = payload.get("detail") or payload.get("error") or payload.get("message")
                if isinstance(detail, str) and detail.strip():
                    return detail.strip()
        except Exception:
            pass

        if response.status_code >= 500:
            return "The server ran into a problem while processing your request. Please try again."
        if response.status_code == 404:
            return "The requested backend endpoint was not found."
        if response.status_code == 400:
            return "The request could not be processed with the current inputs. Please review your selections and try again."
        return "The request could not be completed. Please try again."

    return "Something went wrong. Please try again."


def show_user_error(title: str, response: requests.Response | None = None, exc: Exception | None = None) -> None:
    st.error(f"{title}: {extract_error_message(response=response, exc=exc)}")


def build_param_grid_for_strategy(strategy_name: str, strategy_params: dict) -> dict:
    def clamp_int(value: int, minimum: int = 1) -> list[int]:
        base = int(value)
        return sorted({max(minimum, base - 5), base, base + 5})

    def clamp_float(value: float, step: float = 0.2, minimum: float = 0.1) -> list[float]:
        base = float(value)
        return sorted({
            round(max(minimum, base - step), 4),
            round(base, 4),
            round(base + step, 4),
        })

    if strategy_name == "mean_reversion":
        return {
            "bb_window": clamp_int(strategy_params.get("bb_window", 20), minimum=5),
            "rsi_entry": clamp_float(strategy_params.get("rsi_entry", 30), step=5.0, minimum=5.0),
            "rsi_exit": clamp_float(strategy_params.get("rsi_exit", 70), step=5.0, minimum=10.0),
        }
    if strategy_name == "trend_follower":
        return {
            "ema_fast": clamp_int(strategy_params.get("ema_fast", 20), minimum=2),
            "ema_slow": clamp_int(strategy_params.get("ema_slow", 50), minimum=5),
            "adx_threshold": clamp_float(strategy_params.get("adx_threshold", 25.0), step=5.0, minimum=5.0),
        }
    if strategy_name == "macd":
        return {
            "macd_fast": clamp_int(strategy_params.get("macd_fast", 12), minimum=2),
            "macd_slow": clamp_int(strategy_params.get("macd_slow", 26), minimum=5),
            "squeeze_threshold_quantile": clamp_float(
                strategy_params.get("squeeze_threshold_quantile", 0.2),
                step=0.05,
                minimum=0.05,
            ),
        }
    if strategy_name == "macd_volume_confirmation":
        return {
            "macd_fast": clamp_int(strategy_params.get("macd_fast", 12), minimum=2),
            "macd_slow": clamp_int(strategy_params.get("macd_slow", 26), minimum=5),
            "volume_confirmation_ratio": clamp_float(
                strategy_params.get("volume_confirmation_ratio", 1.2),
                step=0.1,
                minimum=1.0,
            ),
        }
    if strategy_name == "rsi_adx_filter":
        return {
            "rsi_entry": clamp_float(strategy_params.get("rsi_entry", 30), step=5.0, minimum=5.0),
            "rsi_exit": clamp_float(strategy_params.get("rsi_exit", 65), step=5.0, minimum=10.0),
            "adx_threshold": clamp_float(strategy_params.get("adx_threshold", 18.0), step=3.0, minimum=5.0),
        }
    if strategy_name == "rsi_volume_filter":
        return {
            "rsi_entry": clamp_float(strategy_params.get("rsi_entry", 30), step=5.0, minimum=5.0),
            "rsi_exit": clamp_float(strategy_params.get("rsi_exit", 70), step=5.0, minimum=10.0),
            "volume_confirmation_ratio": clamp_float(
                strategy_params.get("volume_confirmation_ratio", 1.1),
                step=0.1,
                minimum=1.0,
            ),
        }
    return {key: [value] for key, value in strategy_params.items()}


def render_risk_report_details(risk_report: dict) -> None:
    if not isinstance(risk_report, dict) or not risk_report:
        st.info("No detailed risk report available yet.")
        return

    summary_rows = [
        ("Overfitting Label", risk_report.get("overfitting_label", "n/a")),
        ("Overfitting Score", risk_report.get("overfitting_score", "n/a")),
        ("Sharpe Decay Ratio", risk_report.get("sharpe_decay_ratio", "n/a")),
        ("Calmar Ratio (OOS)", risk_report.get("calmar_ratio_oos", "n/a")),
        ("OOS Trade Count", risk_report.get("oos_trade_count", "n/a")),
        ("IS Sharpe", risk_report.get("is_sharpe", "n/a")),
        ("OOS Sharpe", risk_report.get("oos_sharpe", "n/a")),
    ]

    details_df = pd.DataFrame(summary_rows, columns=["Metric", "Value"])
    st.dataframe(details_df, use_container_width=True, hide_index=True)

    flags = risk_report.get("flags", [])
    if flags:
        st.markdown("**Risk Flags**")
        for flag in flags:
            st.write(f"- {flag}")
    else:
        st.success("No additional risk flags were raised.")


def render_named_metrics_table(title: str, metrics: dict) -> None:
    st.write(title)
    if not isinstance(metrics, dict) or not metrics:
        st.info("No metrics available.")
        return

    rows = []
    for key, value in metrics.items():
        label = str(key).replace("_", " ").title()
        rows.append({"Metric": label, "Value": value})

    metrics_df = pd.DataFrame(rows)
    st.dataframe(metrics_df, use_container_width=True, hide_index=True)


def render_compact_stat(label: str, value: object) -> None:
    st.markdown(
        f"""
        <div style="
            border:1px solid #e5e7eb;
            border-radius:12px;
            padding:10px 12px;
            background:#fafafa;
            min-height:74px;
        ">
            <div style="font-size:0.75rem; color:#6b7280; margin-bottom:6px;">{label}</div>
            <div style="font-size:1rem; font-weight:600; color:#111827;">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def extract_markdown_title(markdown: str) -> str | None:
    if not isinstance(markdown, str):
        return None
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return None


def create_simple_pdf_bytes(title: str, body: str) -> bytes:
    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "-",
        "\u2026": "...",
        "\xa0": " ",
    }

    def ascii_safe(text: str) -> str:
        cleaned = str(text)
        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)
        cleaned = "".join(ch if 32 <= ord(ch) <= 126 or ch in "\n\t" else " " for ch in cleaned)
        cleaned = " ".join(cleaned.split())
        return cleaned

    def pdf_escape(text: str) -> str:
        safe = ascii_safe(text)
        return safe.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def clean_markdown(text: str) -> str:
        if not isinstance(text, str):
            return ""
        cleaned = text.strip()
        for token in ("**", "__", "`", "#"):
            cleaned = cleaned.replace(token, "")
        cleaned = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", cleaned)
        cleaned = re.sub(r"(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)", r"\1", cleaned)
        cleaned = re.sub(r"(?<!_)_(?!_)(.*?)(?<!_)_(?!_)", r"\1", cleaned)
        cleaned = cleaned.replace("*", "")
        cleaned = cleaned.replace("_", " ")
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()

    def wrap_text(text: str, max_chars: int) -> list[str]:
        words = str(text).split()
        if not words:
            return [""]
        lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            tentative = f"{current} {word}"
            if len(tentative) <= max_chars:
                current = tentative
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    def is_table_separator(line: str) -> bool:
        stripped = line.strip()
        if not stripped or "|" not in stripped:
            return False
        allowed = set("|:- ")
        return all(ch in allowed for ch in stripped)

    def parse_table_row(line: str) -> list[str]:
        parts = [clean_markdown(part.strip()) for part in line.strip().strip("|").split("|")]
        return [part for part in parts if part]

    def render_table_blocks(table_lines: list[str]) -> list[tuple[str, str]]:
        if len(table_lines) < 2:
            return [("body", ascii_safe(line)) for line in table_lines if ascii_safe(line)]

        header = parse_table_row(table_lines[0])
        data_rows = []
        for raw_line in table_lines[1:]:
            if is_table_separator(raw_line):
                continue
            row = parse_table_row(raw_line)
            if row:
                data_rows.append(row)

        blocks: list[tuple[str, str]] = []
        for row in data_rows:
            strategy_name = row[0] if row else "Strategy"
            blocks.append(("h3", strategy_name))
            for idx, value in enumerate(row[1:], start=1):
                header_label = header[idx] if idx < len(header) else f"Metric {idx}"
                blocks.append(("body", f"{header_label}: {value}"))
            blocks.append(("spacer", ""))
        return blocks

    raw_lines = body.splitlines() if isinstance(body, str) else []
    if raw_lines and raw_lines[0].strip().startswith("# "):
        first_heading = clean_markdown(raw_lines[0])
        if first_heading == clean_markdown(title):
            raw_lines = raw_lines[1:]

    content_blocks: list[tuple[str, str]] = [("title", clean_markdown(title))]
    content_blocks.append(("meta", "Generated by Stratify"))
    content_blocks.append(("spacer", ""))

    idx = 0
    while idx < len(raw_lines):
        raw_line = raw_lines[idx]
        stripped = raw_line.strip()
        if not stripped:
            content_blocks.append(("spacer", ""))
            idx += 1
            continue

        if "|" in stripped:
            table_lines = [raw_line]
            look_ahead = idx + 1
            while look_ahead < len(raw_lines):
                next_line = raw_lines[look_ahead].strip()
                if not next_line or "|" not in next_line:
                    break
                table_lines.append(raw_lines[look_ahead])
                look_ahead += 1

            if len(table_lines) >= 2 and any(is_table_separator(line) for line in table_lines[1:]):
                content_blocks.extend(render_table_blocks(table_lines))
                idx = look_ahead
                continue

        if stripped.startswith("### "):
            content_blocks.append(("h3", clean_markdown(stripped[4:])))
        elif stripped.startswith("## "):
            content_blocks.append(("h2", clean_markdown(stripped[3:])))
        elif stripped.startswith(("- ", "* ")):
            content_blocks.append(("bullet", clean_markdown(stripped[2:])))
        elif stripped[:2].isdigit() and stripped[2:4] == ". ":
            content_blocks.append(("bullet", clean_markdown(stripped[4:])))
        else:
            content_blocks.append(("body", clean_markdown(stripped)))
        idx += 1

    style_map = {
        "title": {"font": "F2", "size": 22, "leading": 28, "max_chars": 44, "indent": 50},
        "meta": {"font": "F1", "size": 10, "leading": 16, "max_chars": 70, "indent": 50},
        "h2": {"font": "F2", "size": 15, "leading": 22, "max_chars": 58, "indent": 50},
        "h3": {"font": "F2", "size": 12, "leading": 18, "max_chars": 64, "indent": 50},
        "body": {"font": "F1", "size": 11, "leading": 16, "max_chars": 80, "indent": 50},
        "bullet": {"font": "F1", "size": 11, "leading": 16, "max_chars": 72, "indent": 68},
        "spacer": {"font": "F1", "size": 11, "leading": 10, "max_chars": 1, "indent": 50},
        "footer": {"font": "F1", "size": 9, "leading": 12, "max_chars": 40, "indent": 50},
    }

    pages: list[list[tuple[str, str]]] = [[]]
    current_y = 770
    bottom_margin = 60

    def ensure_space(lines_needed: int, leading: int) -> None:
        nonlocal current_y
        needed = lines_needed * leading
        if current_y - needed < bottom_margin:
            pages.append([])
            current_y = 770

    for style, text in content_blocks:
        cfg = style_map[style]
        wrapped_lines = wrap_text(text, cfg["max_chars"]) if style != "spacer" else [""]
        ensure_space(len(wrapped_lines), cfg["leading"])
        for line_idx, wrapped_line in enumerate(wrapped_lines):
            line_text = wrapped_line
            if style == "bullet" and line_idx == 0:
                line_text = f"- {wrapped_line}"
            pages[-1].append((style, line_text))
            current_y -= cfg["leading"]

    if pages and not pages[-1]:
        pages.pop()

    objects = []

    def add_object(content: str) -> int:
        objects.append(content)
        return len(objects)

    font_regular_obj = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    font_bold_obj = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
    page_ids = []

    for page_number, page_lines in enumerate(pages, start=1):
        stream_parts = []
        current_y = 770

        for style, line in page_lines:
            cfg = style_map[style]
            font_ref = "F2" if cfg["font"] == "F2" else "F1"
            escaped = pdf_escape(str(line)[:180])
            stream_parts.append(
                f"BT /{font_ref} {cfg['size']} Tf 1 0 0 1 {cfg['indent']} {current_y} Tm ({escaped}) Tj ET"
            )
            current_y -= cfg["leading"]

        footer_cfg = style_map["footer"]
        footer_text = pdf_escape(f"Page {page_number} of {len(pages)}")
        stream_parts.append(
            f"BT /F1 {footer_cfg['size']} Tf 1 0 0 1 500 28 Tm ({footer_text}) Tj ET"
        )

        stream = "\n".join(stream_parts)
        content_obj = add_object(
            f"<< /Length {len(stream.encode('latin-1', errors='replace'))} >>\nstream\n{stream}\nendstream"
        )
        page_obj = add_object(
            f"<< /Type /Page /Parent 0 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_regular_obj} 0 R /F2 {font_bold_obj} 0 R >> >> "
            f"/Contents {content_obj} 0 R >>"
        )
        page_ids.append(page_obj)

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    pages_obj = add_object(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>")

    for page_id in page_ids:
        objects[page_id - 1] = objects[page_id - 1].replace("/Parent 0 0 R", f"/Parent {pages_obj} 0 R")

    catalog_obj = add_object(f"<< /Type /Catalog /Pages {pages_obj} 0 R >>")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj_idx, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{obj_idx} 0 obj\n{obj}\nendobj\n".encode("latin-1", errors="replace"))

    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_obj} 0 R >>\nstartxref\n{xref_start}\n%%EOF".encode(
            "latin-1"
        )
    )
    return bytes(pdf)


def build_strategy_report_payload(
    data: dict,
    market_context: dict,
    generated_strategies: list[dict],
    evaluations: dict,
) -> dict:
    strategy_backtests = {}
    strategy_risks = {}
    strategy_optimizations = []

    for strategy_index, evaluation in evaluations.items():
        if not isinstance(evaluation, dict):
            continue
        strategy_name = evaluation.get("strategy_name", f"strategy_{strategy_index}")
        strategy_backtests[strategy_name] = evaluation.get("backtest_result", {})
        strategy_risks[strategy_name] = (
            evaluation.get("backtest_result", {}).get("risk_report", {})
            if isinstance(evaluation.get("backtest_result", {}), dict)
            else {}
        )
        strategy_optimizations.append(
            {
                "strategy_name": strategy_name,
                "best_params": evaluation.get("best_params", {}),
                "optimization_summary": evaluation.get("optimization_result", {}),
            }
        )

    return {
        "ticker": data["ticker"],
        "start_date": data["start_date"],
        "end_date": data["end_date"],
        "market_context": market_context,
        "strategy_specs": generated_strategies,
        "backtest_results": strategy_backtests,
        "risk_results": strategy_risks,
        "optimization_results": strategy_optimizations,
    }


def evaluate_generated_strategy_task(
    data: dict,
    strategy: dict,
    initial_capital: float,
) -> dict:
    optimization_payload = {
        "ticker": data["ticker"],
        "start_date": data["start_date"],
        "end_date": data["end_date"],
        "initial_capital": float(initial_capital),
        "strategy_name": strategy["strategy_name"],
        "param_grid": build_param_grid_for_strategy(
            strategy["strategy_name"],
            strategy["strategy_params"],
        ),
        "is_split": 0.7,
    }
    optimization_response = requests.post(AGENT_OPTIMIZE_URL, json=optimization_payload, timeout=180)
    optimization_response.raise_for_status()
    optimization_result = optimization_response.json()
    best_params = (
        optimization_result.get("top_configs", [{}])[0].get("params")
        if optimization_result.get("top_configs")
        else strategy["strategy_params"]
    )

    backtest_payload = {
        "ticker": data["ticker"],
        "start_date": data["start_date"],
        "end_date": data["end_date"],
        "initial_capital": float(initial_capital),
        "strategy_name": strategy["strategy_name"],
        "strategy_params": best_params,
        "is_split": 0.7,
    }
    backtest_response = requests.post(AGENT_BACKTEST_URL, json=backtest_payload, timeout=120)
    backtest_response.raise_for_status()
    backtest_result = backtest_response.json()

    return {
        "strategy_name": strategy["strategy_name"],
        "optimization_result": optimization_result,
        "backtest_result": backtest_result,
        "best_params": best_params,
    }


def generate_strategy_report_task(report_payload: dict) -> dict:
    report_response = requests.post(AGENT_REPORT_URL, json=report_payload, timeout=180)
    report_response.raise_for_status()
    return report_response.json()


@st.fragment(run_every="2s")
def render_strategy_report_panel(
    data: dict,
    market_context: dict,
    generated_strategies: list[dict],
    backtestable_indices: list[int],
) -> None:
    stored_evaluations = st.session_state.get("strategy_generated_all_evaluations", {})
    background_futures = st.session_state.get("strategy_generated_background_futures", {})
    report_future = st.session_state.get("strategy_generated_report_future")

    completed_now = False
    for idx, future in list(background_futures.items()):
        if future.done() and idx not in stored_evaluations:
            try:
                stored_evaluations[idx] = future.result()
                completed_now = True
            except Exception as exc:
                stored_evaluations[idx] = {"error": str(exc)}
                completed_now = True

    if completed_now:
        st.session_state["strategy_generated_all_evaluations"] = stored_evaluations

    all_background_done = bool(backtestable_indices) and all(
        idx in stored_evaluations for idx in backtestable_indices
    )
    if all_background_done and report_future is None and st.session_state.get("strategy_generated_report_result") is None:
        report_payload = build_strategy_report_payload(
            data=data,
            market_context=market_context,
            generated_strategies=generated_strategies,
            evaluations=stored_evaluations,
        )
        report_future = BACKGROUND_EXECUTOR.submit(generate_strategy_report_task, report_payload)
        st.session_state["strategy_generated_report_future"] = report_future

    if report_future is not None and report_future.done() and st.session_state.get("strategy_generated_report_result") is None:
        try:
            st.session_state["strategy_generated_report_result"] = report_future.result()
            st.session_state["strategy_generated_report_future"] = None
        except Exception:
            st.session_state["strategy_generated_report_result"] = None
            st.session_state["strategy_generated_report_future"] = None

    report_result = st.session_state.get("strategy_generated_report_result")
    if report_result:
        report_title = extract_markdown_title(report_result.get("markdown", ""))
        if report_title:
            st.markdown(f"### {report_title}")
        pdf_bytes = create_simple_pdf_bytes(
            title=report_title or f"{data['ticker']} Strategy Report",
            body=report_result.get("markdown", ""),
        )
        st.download_button(
            "Download PDF Report",
            data=pdf_bytes,
            file_name=f"strategy_report_{data['ticker']}_{data['start_date']}_{data['end_date']}.pdf",
            mime="application/pdf",
            use_container_width=False,
            key="download_strategy_report_pdf",
        )
        st.write(report_result.get("summary", "No summary available."))

        for section_name, section_content in report_result.get("sections", {}).items():
            with st.expander(section_name):
                st.markdown(section_content)
        return

    ready_count = sum(
        1 for idx in backtestable_indices if idx in stored_evaluations and "error" not in stored_evaluations[idx]
    )
    total_count = len(backtestable_indices)
    if total_count == 0:
        st.info("No backtestable generated strategies are available for reporting.")
    else:
        st.info(f"Background evaluation progress: {ready_count}/{total_count} strategies completed. The report will appear automatically once all evaluations are ready.")


def render_header():
    left_col, right_col = st.columns([4, 2])

    with left_col:
        st.title("Stratify")
        st.caption("Market intelligence, backtesting, and AI-assisted strategy generation in one workspace.")

    with right_col:
        st.markdown(
            """
            <div style="display:flex; justify-content:flex-end; align-items:center; gap:12px; margin-top:8px;">
                <div style="text-align:right;">
                    <div style="font-size:0.8rem; color:#6b7280;">Profile</div>
                    <div style="font-weight:600;">MVP User</div>
                </div>
                <div style="
                    width:42px;
                    height:42px;
                    border-radius:999px;
                    background:linear-gradient(135deg, #1d4ed8, #0f766e);
                    color:white;
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    font-weight:700;
                    font-size:0.95rem;
                ">MU</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tier_options = ["Free", "Pro", "Advanced"]
        try:
            selected_tier = st.segmented_control(
                "Tier",
                options=tier_options,
                default=st.session_state["selected_tier"],
                key="tier_selector",
                help="Toggle the MVP tiers to preview what each user level can access.",
            )
        except Exception:
            selected_tier = st.radio(
                "Tier",
                options=tier_options,
                index=tier_options.index(st.session_state["selected_tier"]),
                key="tier_selector_fallback",
                horizontal=True,
                help="Toggle the MVP tiers to preview what each user level can access.",
            )
        st.session_state["selected_tier"] = selected_tier
        st.caption(TIER_COPY[st.session_state["selected_tier"]])


def render_market_intelligence_tab(active_tier: str):
    st.subheader("Market Intelligence")
    st.caption("Fetch a quick company snapshot, recent news, and an AI summary.")

    if not tier_enabled(active_tier, "Pro"):
        st.info("Available from the Pro tier onward. Switch the tier at the top right to unlock this tab.")
        return

    with st.form("market_intel_form"):
        ticker = st.selectbox("Ticker", options=ASSETS, index=0)
        submitted = st.form_submit_button("Fetch Market Intelligence", use_container_width=True)

    market_intel_signature = (ticker,)
    if st.session_state.get("market_intel_signature") != market_intel_signature:
        clear_market_intelligence_results()
        st.session_state["market_intel_signature"] = market_intel_signature

    if submitted:
        try:
            with st.spinner(f"Fetching market intelligence for {ticker}..."):
                response = requests.get(f"{MARKET_INTEL_URL}/{ticker}", timeout=30)

            if response.status_code != 200:
                st.session_state["market_intel_result"] = {
                    "request_error": f"API error {response.status_code}",
                    "response_body": response.text,
                }
            else:
                st.session_state["market_intel_result"] = response.json()
        except Exception as exc:
            st.session_state["market_intel_result"] = {
                "request_error": "Backend connection failed",
                "response_body": str(exc),
            }

    data = st.session_state["market_intel_result"]

    if not data:
        st.info("Choose a ticker and fetch market intelligence.")
        return

    if "request_error" in data:
        st.error(data["request_error"])
        return

    if "error" in data:
        st.error(data["error"])
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Ticker", data["ticker"])
    with col2:
        st.metric("Revenue", f"${data['revenue']:,.0f}")
    with col3:
        st.metric("EPS", f"{data['eps']:.2f}")

    sentiment = data.get("sentiment", "Neutral")
    if sentiment == "Positive":
        st.success(f"Sentiment: {sentiment}")
    elif sentiment == "Negative":
        st.error(f"Sentiment: {sentiment}")
    else:
        st.info(f"Sentiment: {sentiment}")

    st.subheader("AI Summary")
    st.write(data.get("llm_summary", "No AI summary available."))

    st.subheader("Recent News")
    for article in data.get("news", []):
        with st.container(border=True):
            st.markdown(f"**{article.get('title', 'Untitled article')}**")
            if article.get("url"):
                st.markdown(f"[Open article]({article['url']})")


def render_backtester_tab(active_tier: str):
    st.subheader("Backtester")
    st.caption("Configure a strategy and run it against historical data.")

    strategy_options = list(STRATEGIES.items())
    control_box = st.container(border=True)
    with control_box:
        col1, col2, col3 = st.columns(3)
        with col1:
            strategy_label = st.selectbox(
                "Strategy",
                options=[label for label, _ in strategy_options],
            )
        with col2:
            mode = st.radio(
                "Mode",
                options=["Single Asset", "Portfolio"],
                horizontal=True,
                index=["Single Asset", "Portfolio"].index(st.session_state["backtest_mode"]),
                key="backtest_mode_widget",
            )
        with col3:
            initial_capital = st.number_input("Initial Capital", min_value=1000, value=10000, step=1000)

        st.session_state["backtest_mode"] = mode

        if mode == "Single Asset":
            single_asset = st.selectbox(
                "Ticker",
                options=ASSETS,
                index=ASSETS.index(st.session_state["backtest_single_asset_value"]),
                key="backtest_single_asset",
            )
            st.session_state["backtest_single_asset_value"] = single_asset
            assets = [single_asset]
        else:
            assets = st.multiselect(
                "Tickers",
                options=ASSETS,
                default=st.session_state["backtest_portfolio_assets"],
                key="backtest_portfolio_assets_widget",
            )
            st.session_state["backtest_portfolio_assets"] = assets
            st.caption(f"{len(assets)} ticker(s) selected")

        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("Start Date", value=DEFAULT_BACKTEST_START, key="backtest_start")
        with date_col2:
            end_date = st.date_input("End Date", value=DEFAULT_BACKTEST_END, key="backtest_end")

        strategy = STRATEGIES[strategy_label]
        params = {}
        if strategy == "mean_reversion":
            st.markdown(
                '<p style="color:black; font-size:1.05rem; margin-bottom:0;">'
                '<b>Mean Reversion (RSI + Bollinger)</b> — buys oversold dips and sells overbought bounces.</p>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<p style="color:black; font-size:0.95rem; margin-top:0;">'
                '📈 <b>Buy signal:</b> RSI drops below the oversold threshold <b>or</b> price touches the lower Bollinger Band.<br>'
                '📉 <b>Exit signal:</b> RSI rises above the overbought threshold <b>and</b> price reaches the upper Bollinger Band.</p>',
                unsafe_allow_html=True,
            )
            with st.expander("How does this strategy work?"):
                st.markdown(
                    "The **Relative Strength Index**, or RSI, measures recent price momentum on a scale from 0 to 100. "
                    "When RSI falls below a certain threshold, it suggests the stock has dropped quickly and may be "
                    "oversold, meaning a price rebound could be likely.\n\n"
                    "**Bollinger Bands**, on the other hand, track how far the price moves relative to its recent average. "
                    "They consist of a moving average with upper and lower bands based on standard deviation. When the "
                    "price touches the lower band, it indicates the stock is trading lower than usual compared to its "
                    "recent range, which may signal a potential buying opportunity.\n\n"
                    "A long position is opened when **either** condition fires (RSI oversold **or** lower-band touch) "
                    "and closed only when **both** conditions reverse (RSI overbought **and** upper-band touch). "
                    "This asymmetry keeps you in winning trades longer while still catching quick dips."
                )
            p1, p2 = st.columns(2)
            with p1:
                params["rsi_low"] = st.slider(
                    "RSI Oversold", 10, 50, 30,
                    help="Buy signal threshold — lower values require a deeper dip before entering.",
                )
            with p2:
                params["rsi_high"] = st.slider(
                    "RSI Overbought", 50, 90, 70,
                    help="Sell signal threshold — higher values hold positions longer before exiting.",
                )
            p3, p4 = st.columns(2)
            with p3:
                params["bb_window"] = st.slider(
                    "Bollinger Window", 10, 50, 20,
                    help="Lookback period (days) for the moving average and bands. Shorter = more reactive.",
                )
            with p4:
                params["bb_std"] = st.slider(
                    "Bollinger Std Dev", 1.0, 3.5, 2.0, step=0.1,
                    help="Band width in standard deviations. Wider bands = fewer but higher-conviction signals.",
                )
        elif strategy == "trend_follower":
            st.markdown(
                '<p style="color:black; font-size:1.05rem; margin-bottom:0;">'
                '<b>Trend Follower (EMA + ADX)</b> — rides sustained directional moves.</p>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<p style="color:black; font-size:0.95rem; margin-top:0;">'
                '📈 <b>Buy signal:</b> fast EMA is above slow EMA while ADX confirms a strong trend (ADX &gt; threshold).<br>'
                '📉 <b>Exit signal:</b> fast EMA crosses back below slow EMA.</p>',
                unsafe_allow_html=True,
            )
            with st.expander("How does this strategy work?"):
                st.markdown(
                    "Two **Exponential Moving Averages** (fast and slow) track price momentum. "
                    "When the fast EMA is above the slow EMA the market is in an uptrend.\n\n"
                    "The **ADX (Average Directional Index)** measures trend *strength* regardless of direction. "
                    "An ADX reading above the threshold confirms the trend is strong enough to trade.\n\n"
                    "A long position is held for as long as the fast EMA stays above the slow EMA **and** ADX confirms trend strength. "
                    "The position is exited only when the fast EMA crosses below the slow EMA, "
                    "which avoids premature exits during minor pullbacks."
                )
            p1, p2, p3 = st.columns(3)
            with p1:
                params["ema_short"] = st.slider(
                    "EMA Short", 5, 50, 20,
                    help="Fast moving average period. Shorter = more responsive to recent price changes.",
                )
            with p2:
                params["ema_long"] = st.slider(
                    "EMA Long", 20, 200, 50,
                    help="Slow moving average period. Longer = smoother trend baseline.",
                )
            with p3:
                params["adx_threshold"] = st.slider(
                    "ADX Threshold", 10, 50, 25,
                    help="Minimum ADX value to confirm a trend. Higher = only trade in strong trends.",
                )
        else:
            st.markdown(
                '<p style="color:black; font-size:1.05rem; margin-bottom:0;">'
                '<b>Volatility Breakout (MACD + BB Width)</b> — catches breakouts after volatility squeezes.</p>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<p style="color:black; font-size:0.95rem; margin-top:0;">'
                '📈 <b>Buy signal:</b> Bollinger Band squeeze detected recently and MACD histogram crosses above zero.<br>'
                '📉 <b>Exit signal:</b> MACD histogram crosses below zero (momentum reversal).</p>',
                unsafe_allow_html=True,
            )
            with st.expander("How does this strategy work?"):
                st.markdown(
                    "**Bollinger Band Width** measures volatility. When the bands narrow to historically low levels "
                    "(a *squeeze*), a large price move often follows.\n\n"
                    "The **MACD histogram** shows the difference between the MACD line and its signal line. "
                    "A crossover from negative to positive indicates upward momentum is accelerating.\n\n"
                    "The strategy enters when a squeeze has occurred in a recent lookback window (last 5 bars) "
                    "and the MACD histogram turns positive. "
                    "It exits when the histogram turns negative, signaling momentum has reversed."
                )
            p1, p2 = st.columns(2)
            with p1:
                params["macd_fast"] = st.slider(
                    "MACD Fast", 5, 20, 12,
                    help="Fast EMA period for MACD calculation. Shorter = more sensitive to recent moves.",
                )
            with p2:
                params["macd_slow"] = st.slider(
                    "MACD Slow", 20, 50, 26,
                    help="Slow EMA period for MACD calculation. Longer = smoother signal line.",
                )

        params["initial_capital"] = initial_capital
        submitted = st.button("Run Backtest", type="primary", use_container_width=True, key="run_backtest_button")

    backtest_signature = (
        strategy,
        mode,
        tuple(assets),
        str(start_date),
        str(end_date),
        tuple(sorted(params.items())),
    )
    if st.session_state.get("backtest_signature") != backtest_signature:
        clear_backtest_results()
        st.session_state["backtest_signature"] = backtest_signature

    if submitted:
        if not assets:
            st.warning("Please select at least one ticker.")
        else:
            config = {
                "assets": assets,
                "start_date": start_date,
                "end_date": end_date,
                "strategy": strategy,
                "params": params,
            }
            payload = build_payload(config)
            endpoint = get_backtest_endpoint(strategy, assets)
            try:
                with st.spinner("Running backtest..."):
                    response = requests.post(endpoint, json=payload, timeout=60)
                if response.status_code != 200:
                    show_user_error("Backtest failed", response=response)
                else:
                    st.session_state["backtest_data"] = response.json()
                    st.session_state["backtest_strategy"] = strategy
                    st.session_state["backtest_config"] = config
                    st.session_state["risk_analysis_data"] = None
                    st.session_state["ai_insights_data"] = None
            except requests.RequestException as exc:
                st.error(f"Could not reach backend API. Details: {exc}")

    st.caption(f"Current tier: `{active_tier}`. Free users can use all three built-in strategies and optional portfolio backtests.")

    data = st.session_state["backtest_data"]
    strategy = st.session_state["backtest_strategy"]
    if not data or not strategy:
        st.info("Run a backtest to view results here.")
        return

    st.divider()
    if "portfolio_metrics" not in data:
        st.subheader("Metrics")
        st.json(data.get("metrics", {}))
        signal_rows = data.get("signal_rows", [])
        if signal_rows:
            df = pd.DataFrame(signal_rows)
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"])
                st.line_chart(df.set_index("Date")[["strategy_eq", "buyhold_eq"]])
            st.subheader("Signal Rows")
            st.dataframe(df.tail(50), use_container_width=True, hide_index=True)
        return

    if strategy == "mean_reversion":
        render_metrics_mean_reversion(data)
        render_charts_mean_reversion(data)
    elif strategy == "trend_follower":
        render_metrics_trend(data)
        render_charts_trend(data)
    elif strategy == "macd":
        render_metrics_breakout(data)
        render_charts_breakout(data)

    # Pro-tier: Risk Analysis (overfitting detection)
    if tier_enabled(active_tier, "Pro") and "portfolio_metrics" in data:
        st.markdown("---")
        st.markdown(
            '<h3 style="text-decoration:underline;"><b>🔍 Risk Analysis (Overfitting Detection)</b></h3>',
            unsafe_allow_html=True,
        )
        if st.button("Run Risk Analysis", key="risk_btn", type="primary"):
            with st.spinner("Running overfitting analysis (70/30 IS/OOS split)..."):
                try:
                    payload = build_payload(st.session_state.get("backtest_config", {}))
                    resp = requests.post(RISK_ANALYSIS_URL, json=payload, timeout=120)
                    if resp.status_code == 200:
                        st.session_state["risk_analysis_data"] = resp.json()
                    else:
                        show_user_error("Risk analysis failed", response=resp)
                except requests.RequestException as exc:
                    show_user_error("Risk analysis failed", exc=exc)

        risk_data = st.session_state.get("risk_analysis_data")
        if risk_data:
            render_risk_analysis(risk_data)

    # Pro-tier: AI Insights (Cohere)
    if tier_enabled(active_tier, "Pro") and "portfolio_metrics" in data:
        st.markdown("---")
        st.markdown(
            '<h3 style="text-decoration:underline;"><b>🤖 AI Insights</b></h3>',
            unsafe_allow_html=True,
        )
        if st.button("Generate AI Insights", key="ai_insights_btn", type="primary"):
            with st.spinner("Generating AI insights via Cohere..."):
                try:
                    config = st.session_state.get("backtest_config", {})
                    insights_payload = {
                        "strategy_name": config.get("strategy", strategy),
                        "portfolio_metrics": data.get("portfolio_metrics", {}),
                        "benchmark": data.get("benchmark", {}),
                        "risk_analysis": st.session_state.get("risk_analysis_data") or {},
                        "tickers": data.get("tickers", []),
                        "strategy_params": config.get("params", {}),
                    }
                    resp = requests.post(AI_INSIGHTS_URL, json=insights_payload, timeout=90)
                    if resp.status_code == 200:
                        st.session_state["ai_insights_data"] = resp.json()
                    else:
                        show_user_error("AI insights failed", response=resp)
                except requests.RequestException as exc:
                    show_user_error("AI insights failed", exc=exc)

        ai_data = st.session_state.get("ai_insights_data")
        if ai_data:
            render_ai_insights(ai_data)


def render_strategy_generation_tab(active_tier: str):
    st.subheader("Strategy Generation")
    st.caption("Market context is analyzed first, then strategy ideas are generated from that context.")

    if not tier_enabled(active_tier, "Advanced"):
        st.info("Available only on the Advanced tier. Switch the tier at the top right to access strategy generation.")
        return

    control_box = st.container(border=True)
    with control_box:
        row1, row2 = st.columns([2, 1])
        with row1:
            ticker = st.selectbox("Ticker", options=ASSETS, index=0, key="gen_ticker")

        row3, row4 = st.columns(2)
        with row3:
            start_date = st.date_input("Start Date", value=DEFAULT_GENERATION_START, key="gen_start")
        with row4:
            end_date = st.date_input("End Date", value=DEFAULT_GENERATION_END, key="gen_end")

        use_llm = st.toggle("Use Cohere if available", value=True)
        submitted = st.button("Generate Strategies", use_container_width=True, key="generate_strategies_button")

    strategy_generation_signature = (
        ticker,
        str(start_date),
        str(end_date),
        use_llm,
    )
    if st.session_state.get("strategy_generation_signature") != strategy_generation_signature:
        clear_strategy_generation_results()
        st.session_state["strategy_generation_signature"] = strategy_generation_signature

    if submitted:
        cache = st.session_state.get("strategy_generation_cache", {})
        cached_run = cache.get(strategy_generation_signature)
        if isinstance(cached_run, dict):
            run_demo_loading_step("Analyzing market context...", seconds=3.0)
            run_demo_loading_step("Generating strategy candidates...", seconds=3.0)
            st.session_state["strategy_generation_market_context"] = cached_run.get("market_context")
            st.session_state["strategy_generation_result"] = cached_run.get("result")
            reset_strategy_generation_downstream_results()
        else:
            try:
                market_context_payload = {
                    "ticker": ticker,
                    "start_date": str(start_date),
                    "end_date": str(end_date),
                }
                with st.spinner("Analyzing market context..."):
                    context_response = requests.post(
                        AGENT_MARKET_CONTEXT_URL,
                        json=market_context_payload,
                        timeout=120,
                    )
                if context_response.status_code != 200:
                    show_user_error("Market context could not be prepared", response=context_response)
                    return

                market_context = context_response.json()
                st.session_state["strategy_generation_market_context"] = market_context

                payload = {
                    "ticker": ticker,
                    "start_date": str(start_date),
                    "end_date": str(end_date),
                    "market_context": market_context,
                    "use_llm": use_llm,
                    "allow_experimental": True,
                }
                with st.spinner("Generating strategy candidates... This can take a little longer when research retrieval and Cohere are both used."):
                    response = requests.post(STRATEGY_GENERATION_URL, json=payload, timeout=180)
                if response.status_code != 200:
                    show_user_error("Strategy generation failed", response=response)
                else:
                    result = response.json()
                    st.session_state["strategy_generation_result"] = result
                    reset_strategy_generation_downstream_results()
                    cache[strategy_generation_signature] = {
                        "market_context": market_context,
                        "result": result,
                    }
                    st.session_state["strategy_generation_cache"] = cache
            except requests.RequestException as exc:
                show_user_error("Strategy generation failed", exc=exc)

    data = st.session_state["strategy_generation_result"]
    if not data:
        st.info("Generate strategies to view candidates here.")
        return

    st.divider()
    st.subheader("Research Setup")
    meta1, meta2, meta3, meta4 = st.columns(4)
    with meta1:
        st.metric("Ticker", data["ticker"])
    with meta2:
        st.metric("Start", data["start_date"])
    with meta3:
        st.metric("End", data["end_date"])
    with meta4:
        st.metric("Candidates", len(data.get("strategies", [])))

    context = st.session_state.get("strategy_generation_market_context") or data.get("market_context", {})
    if context:
        st.subheader("Market Context")
        st.caption("This context guides the generated strategy ideas.")

        context_col1, context_col2, context_col3 = st.columns(3)
        with context_col1:
            render_compact_stat("Market Regime", str(context.get("regime", "n/a")).replace("_", " ").title())
            render_compact_stat("Strategy Bias", str(context.get("strategy_bias", "n/a")).replace("_", " ").title())
        with context_col2:
            render_compact_stat("Trend Direction", str(context.get("trend_direction", "n/a")).replace("_", " ").title())
            render_compact_stat("30D Realized Vol", context.get("realized_vol_30d", "n/a"))
        with context_col3:
            render_compact_stat("SPY Correlation", context.get("correlation_to_spy", "n/a"))
            render_compact_stat("SMA 200 Slope", context.get("sma_200_slope", "n/a"))

        reasoning = context.get("reasoning", "")
        if reasoning:
            with st.expander("Why this context was identified"):
                st.write(reasoning)

    generated_strategies = data.get("strategies", [])
    if not generated_strategies:
        st.warning("No strategies were generated for this setup.")
        return

    background_futures = st.session_state.get("strategy_generated_background_futures", {})
    stored_evaluations = st.session_state.get("strategy_generated_all_evaluations", {})
    report_future = st.session_state.get("strategy_generated_report_future")

    if submitted:
        generated_initial_capital = float(st.session_state.get("generated_strategy_initial_capital", 10000))
        for idx, strategy in enumerate(generated_strategies):
            if strategy.get("backtestable", False):
                background_futures[idx] = BACKGROUND_EXECUTOR.submit(
                    evaluate_generated_strategy_task,
                    data,
                    strategy,
                    generated_initial_capital,
                )
        st.session_state["strategy_generated_background_futures"] = background_futures

    completed_now = False
    for idx, future in list(background_futures.items()):
        if future.done() and idx not in stored_evaluations:
            try:
                stored_evaluations[idx] = future.result()
                completed_now = True
            except Exception as exc:
                stored_evaluations[idx] = {"error": str(exc)}
                completed_now = True

    if completed_now:
        st.session_state["strategy_generated_all_evaluations"] = stored_evaluations

    backtestable_indices = [
        idx for idx, strategy in enumerate(generated_strategies) if strategy.get("backtestable", False)
    ]

    all_background_done = bool(backtestable_indices) and all(
        idx in stored_evaluations for idx in backtestable_indices
    )
    if all_background_done and report_future is None and st.session_state.get("strategy_generated_report_result") is None:
        report_payload = build_strategy_report_payload(
            data=data,
            market_context=context,
            generated_strategies=generated_strategies,
            evaluations=stored_evaluations,
        )
        report_future = BACKGROUND_EXECUTOR.submit(generate_strategy_report_task, report_payload)
        st.session_state["strategy_generated_report_future"] = report_future

    if report_future is not None and report_future.done() and st.session_state.get("strategy_generated_report_result") is None:
        try:
            st.session_state["strategy_generated_report_result"] = report_future.result()
        except Exception:
            st.session_state["strategy_generated_report_result"] = None
    st.divider()
    st.markdown("## Strategy Evaluation Workspace")
    st.caption("This section contains the generated strategy review area and the overall strategy report.")
    generated_tab, report_tab = st.tabs(["Generated Strategies", "Strategy Report"])
    radio_options = backtestable_indices or list(range(len(generated_strategies)))
    selected_index = st.session_state.get("selected_generated_strategy", radio_options[0])
    if selected_index not in radio_options:
        selected_index = radio_options[0]
    selected_strategy = generated_strategies[selected_index]
    selected_backtestable = selected_strategy.get("backtestable", False)
    research_basis = selected_strategy.get("research_basis", [])
    generation_tag = (
        "Cohere Generated"
        if selected_strategy.get("source") == "cohere_grounded"
        else "Research Based"
    )

    with generated_tab:
        st.markdown("**Generated Strategies**")
        st.caption("Choose a strategy, review its details, and render the stored backtest result when ready.")

        selected_index = st.radio(
            "Choose a strategy",
            options=radio_options,
            format_func=lambda idx: generated_strategies[idx]["strategy_name"].replace("_", " ").title(),
            key="selected_generated_strategy",
            horizontal=False,
        )
        selected_strategy = generated_strategies[selected_index]
        selected_backtestable = selected_strategy.get("backtestable", False)
        research_basis = selected_strategy.get("research_basis", [])
        generation_tag = (
            "Cohere Generated"
            if selected_strategy.get("source") == "cohere_grounded"
            else "Research Based"
        )

        selected_strategy_signature = (
            selected_index,
            selected_strategy.get("strategy_name"),
        )
        if st.session_state.get("selected_generated_strategy_signature") != selected_strategy_signature:
            st.session_state["strategy_generated_backtest_result"] = None
            st.session_state["strategy_generated_optimization_result"] = None
            st.session_state["selected_generated_strategy_signature"] = selected_strategy_signature

        with st.container(border=True):
            header_col1, header_col2 = st.columns([5, 1])
            with header_col1:
                st.markdown(f"**{selected_strategy['strategy_name'].replace('_', ' ').title()}**")
                st.caption(selected_strategy.get("description", "No description available."))
            with header_col2:
                st.markdown(
                    f"""
                    <div style="display:flex; justify-content:flex-end; margin-top:4px;">
                        <span style="
                            display:inline-block;
                            padding:6px 10px;
                            border-radius:999px;
                            background:#eef2ff;
                            color:#3730a3;
                            font-size:0.8rem;
                            font-weight:600;
                            border:1px solid #c7d2fe;
                            white-space:nowrap;
                        ">{generation_tag}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            summary_col1, summary_col2 = st.columns(2)
            with summary_col1:
                st.metric("Research Links", len(research_basis))
            with summary_col2:
                st.metric("Status", "Ready" if selected_backtestable else "Idea")

            if selected_strategy.get("rationale"):
                st.write(f"**Why it fits:** {selected_strategy['rationale']}")

            st.warning("AI-generated strategy suggestions can be useful, but they can still be wrong. Review them before relying on them.")

            params_df = pd.DataFrame(
                [
                    {"Parameter": key, "Value": value}
                    for key, value in selected_strategy.get("strategy_params", {}).items()
                ]
            )
            if not params_df.empty:
                with st.expander("View Parameters"):
                    st.dataframe(params_df, use_container_width=True, hide_index=True)

            if research_basis:
                with st.expander("Research Basis"):
                    st.write(", ".join(research_basis))

            if not selected_backtestable:
                st.info(selected_strategy.get("implementation_hint", "This strategy is not ready for backtesting yet."))

        action_box = st.container(border=True)
        with action_box:
            st.subheader("Backtest Selection")
            st.caption("Background evaluation starts automatically after strategies are generated. If this strategy is still running, `Run Backtest` will wait for the remaining work and then render the result.")
            action_col1, action_col2 = st.columns([1, 1])
            with action_col1:
                generated_initial_capital = st.number_input(
                    "Initial Capital",
                    min_value=1000,
                    value=10000,
                    step=1000,
                    key="generated_strategy_initial_capital",
                )
            with action_col2:
                st.write("")
                st.write("")
                run_generated_pipeline = st.button(
                    "Run Backtest",
                    use_container_width=True,
                    key="run_generated_strategy_pipeline",
                    disabled=not selected_backtestable,
                )

            if not selected_backtestable:
                st.caption("Choose a backtestable strategy to enable the backtest run.")

        if run_generated_pipeline and selected_backtestable:
            try:
                future = background_futures.get(selected_index)
                if future is not None:
                    with st.spinner(f"Preparing {selected_strategy['strategy_name'].replace('_', ' ').title()} backtest..."):
                        selected_evaluation = future.result()
                else:
                    selected_evaluation = evaluate_generated_strategy_task(
                        data=data,
                        strategy=selected_strategy,
                        initial_capital=float(generated_initial_capital),
                    )

                stored_evaluations[selected_index] = selected_evaluation
                st.session_state["strategy_generated_all_evaluations"] = stored_evaluations
                st.session_state["strategy_generated_backtest_result"] = {
                    "strategy": selected_strategy,
                    "result": selected_evaluation["backtest_result"],
                    "params": selected_evaluation["best_params"],
                }
                st.session_state["strategy_generated_optimization_result"] = selected_evaluation["optimization_result"]
            except requests.RequestException as exc:
                show_user_error("Backtest failed", exc=exc)
            except Exception as exc:
                show_user_error("Backtest failed", exc=exc)

        all_evaluations = st.session_state.get("strategy_generated_all_evaluations", {})
        pipeline_result = st.session_state.get("strategy_generated_backtest_result")
        if pipeline_result and pipeline_result.get("strategy", {}).get("strategy_name") == selected_strategy["strategy_name"]:
            backtest_result = pipeline_result["result"]
            st.divider()
            st.subheader("Optimization Output")

            optimization_result = st.session_state.get("strategy_generated_optimization_result") or {}
            top_configs = optimization_result.get("top_configs", [])
            if optimization_result.get("fallback_used"):
                st.info(
                    optimization_result.get(
                        "fallback_reason",
                        "Showing the best configs that still produced trades, even though none passed the strict optimization filter.",
                    )
                )
            opt_col1, opt_col2, opt_col3 = st.columns(3)
            with opt_col1:
                st.metric("Candidates Tested", optimization_result.get("total_candidates", 0))
            with opt_col2:
                st.metric("Configs Passed", optimization_result.get("passed", 0))
            with opt_col3:
                st.metric("Best Score", top_configs[0].get("score", "n/a") if top_configs else "n/a")

            best_params = pipeline_result.get("params", selected_strategy.get("strategy_params", {}))
            best_params_df = pd.DataFrame(
                [{"Parameter": key, "Value": value} for key, value in best_params.items()]
            )
            if not best_params_df.empty:
                with st.expander("Best Parameters"):
                    st.dataframe(best_params_df, use_container_width=True, hide_index=True)

            st.subheader("Backtest Output")

            metric1, metric2, metric3 = st.columns(3)
            with metric1:
                st.metric("OOS Sharpe", backtest_result["oos_metrics"].get("sharpe_ratio"))
            with metric2:
                st.metric("OOS Return %", backtest_result["oos_metrics"].get("cumulative_return_pct"))
            with metric3:
                st.metric("Risk Label", backtest_result["risk_report"].get("overfitting_label"))

            split_col1, split_col2 = st.columns(2)
            with split_col1:
                st.caption(f"In-sample end: {backtest_result.get('is_end_date', 'n/a')}")
            with split_col2:
                st.caption(f"Out-of-sample start: {backtest_result.get('oos_start_date', 'n/a')}")

            result_col1, result_col2 = st.columns(2)
            with result_col1:
                render_named_metrics_table("In-Sample", backtest_result.get("is_metrics", {}))
            with result_col2:
                render_named_metrics_table("Out-of-Sample", backtest_result.get("oos_metrics", {}))

            st.subheader("Risk Analysis")
            risk_report = backtest_result.get("risk_report", {})
            risk_col1, risk_col2, risk_col3 = st.columns(3)
            with risk_col1:
                st.metric("Overfitting Score", risk_report.get("overfitting_score"))
            with risk_col2:
                st.metric("Calmar Ratio", risk_report.get("calmar_ratio_oos"))
            with risk_col3:
                st.metric("OOS Trades", risk_report.get("oos_trade_count"))

            if risk_report.get("flags"):
                for flag in risk_report["flags"]:
                    st.warning(flag)

            with st.expander("Full Risk Report"):
                render_risk_report_details(risk_report)
        else:
            ready_count = sum(
                1 for idx in backtestable_indices if idx in stored_evaluations and "error" not in stored_evaluations[idx]
            )
            total_count = len(backtestable_indices)
            st.info(f"Background evaluation progress: {ready_count}/{total_count} backtestable strategies ready.")

    with report_tab:
        st.markdown("**Strategy Report**")
        st.caption("This report summarizes all strategies generated for the current market context and updates automatically once the background evaluations finish.")
        render_strategy_report_panel(data, context, generated_strategies, backtestable_indices)

render_header()
active_tier = st.session_state["selected_tier"]

available_tabs = [("Backtester", render_backtester_tab)]
if tier_enabled(active_tier, "Pro"):
    available_tabs.append(("Market Intelligence", render_market_intelligence_tab))
if tier_enabled(active_tier, "Advanced"):
    available_tabs.append(("Strategy Generation", render_strategy_generation_tab))

tab_labels = [label for label, _ in available_tabs]
tab_containers = st.tabs(tab_labels)

for tab_container, (_, render_fn) in zip(tab_containers, available_tabs):
    with tab_container:
        render_fn(active_tier)
