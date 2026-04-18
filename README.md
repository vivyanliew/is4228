# Strategy Lab — Browser-Based Backtesting & Strategy Research Platform

A browser-based trading strategy research and backtesting platform for finance students and early-stage retail traders. Users can test rule-based technical strategies on historical price data, visualize trade signals, and evaluate performance using standardized metrics — helping them rigorously validate ideas before risking real capital.

A tiered feature model progressively unlocks overfitting detection, AI-generated insights, market intelligence, and a full multi-agent strategy generation pipeline.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Problem Statement](#problem-statement)
3. [Tech Stack](#tech-stack)
4. [Repository Structure](#repository-structure)
5. [Tier Features](#tier-features)
6. [Strategies](#strategies)
7. [Environment Variables](#environment-variables)
8. [Installation & Setup](#installation--setup)
9. [How to Run the Project](#how-to-run-the-project)
10. [API Reference](#api-reference)
11. [Common Issues](#common-issues)

---

## Project Overview

Strategy Lab is a full-stack web application with a **FastAPI backend** and **Streamlit frontend**. It supports two distinct modes of use:

**Rule-based backtesting** - Users select a predefined strategy, configure parameters, choose from 21 assets, and set a date range. The system simulates trades on historical price data, computes performance metrics, and renders interactive visualizations including equity curves, trade signal charts, and drawdown plots. Pro-tier users additionally receive S&P 500 benchmark comparison, overfitting risk analysis (in-sample/out-of-sample), and AI-generated plain-English insights.

**Automated multi-agent pipeline (Advanced tier)** - A sequence of specialized agents orchestrates the full research workflow: market context analysis, LLM-driven strategy generation, backtesting of generated strategies, parameter optimization, risk validation, and synthesis into a structured research report.

---

## Problem Statement

Beginner traders are widely exposed to technical indicators through online content but lack structured tools to validate whether a strategy is robust or simply curve-fitted to historical data. Existing solutions are either too simplistic (charting tools with no backtesting rigor) or too inaccessible (institutional-grade platforms requiring programming expertise). Strategy Lab bridges this gap by embedding methodological best practices like out-of-sample validation, overfitting scoring, benchmark comparison into an accessible, no-code interface.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Backend | FastAPI (Python) |
| Data | yfinance (historical price data) |
| Market Intelligence | Finnhub API (news), Cohere API (AI summaries) |
| AI Insights & Strategy Generation | Cohere API (`command-a-03-2025`) |
| Data processing | pandas, numpy |
| Dependency management | pip + `requirements.txt` |

---

## Repository Structure

```
is4228/
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── main.py                  # FastAPI application entry point
│       ├── routers.py               # Backtesting, risk analysis, AI insights endpoints
│       ├── agent_router.py          # Multi-agent pipeline endpoints
│       ├── models.py                # Pydantic request/response models
│       ├── backtest.py              # Core single-asset backtesting engine
│       ├── portfolio_backtest.py    # Multi-asset portfolio backtesting + SPY benchmark
│       ├── market_intel.py          # Market Intelligence (news, sentiment, AI summary)
│       ├── utils.py                 # Shared utility functions
│       ├── utils_report.py          # Report generation utilities
│       ├── agents/
│       │   ├── market_context_agent.py      # Market regime analysis
│       │   ├── strategy_generation_agent.py # LLM-driven strategy proposal
│       │   ├── backtest_agent.py            # Agent-driven backtesting
│       │   ├── optimization_agent.py        # Parameter optimization
│       │   ├── risk_agent.py                # Overfitting scoring and risk flags
│       │   ├── report_agent.py              # Research report synthesis
│       │   └── strategy_spec.py             # Strategy specification schema
│       ├── strategies/
│       │   ├── strategy_mean_reversion.py   # RSI + Bollinger Bands
│       │   ├── strategy_ema.py              # EMA Crossover + ADX
│       │   └── strategy_macd.py             # MACD + Bollinger Band Squeeze
│       └── research/
│           ├── paper_index.json             # Indexed academic papers
│           └── papers/                      # Source PDFs
├── frontend/
│   ├── app.py          # Main Streamlit application
│   ├── sidebar.py      # Sidebar controls (tier, asset, strategy, date range)
│   ├── api.py          # API endpoint constants and payload builders
│   ├── charts.py       # Chart rendering, risk analysis display, AI insights display
│   ├── metrics.py      # Metrics table rendering
│   └── requirements.txt
└── README.md
```

---

## Tier Features

The application uses a three-tier model selectable from the UI (no authentication required — designed for demo/academic use):

| Tier | Features |
|---|---|
| **Free** | Single and multi-asset portfolio backtesting across 21 assets. All three predefined strategies. S&P 500 benchmark comparison (Alpha, Beta, Information Ratio, Sortino Ratio, Treynor Ratio). Core metrics: cumulative return, annualized return, Sharpe ratio, max drawdown, win rate, trade log, equity curve. |
| **Pro** | All Free features, plus: overfitting risk analysis (in-sample/out-of-sample 70/30 split with scored risk flag), AI-generated insights (performance analysis, risk commentary, actionable parameter guidance), and Market Intelligence (news feed, sentiment tagging, AI company snapshot). |
| **Advanced** | All Pro features, plus: full automated Strategy Generation pipeline — market context analysis, LLM-driven strategy proposals, parameter optimization, backtesting of generated strategies, and a synthesized research report. |

**Supported assets (21):** AAPL, NVDA, MSFT, GOOGL, TSLA, AMD, NFLX, META, AMZN, WMT, COST, SBUX, JPM, GS, BRK-B, V, UNH, LLY, XOM, CVX, BTC-USD

---

## Strategies

### Mean Reversion — RSI + Bollinger Bands

- **Entry:** Price at or below the lower Bollinger Band and RSI below 30 (oversold)
- **Exit:** Price at or above the upper Bollinger Band or RSI above 70 (overbought)
- **Rationale:** Captures price reversion in range-bound markets; the most intuitive starting strategy for beginner users

### Trend Follower — EMA Crossover + ADX

- **Entry:** 20-period EMA crosses above the 50-period EMA, with ADX above 25 confirming trend strength
- **Exit:** EMA crossover reverses
- **Rationale:** Teaches users that crossover signals require trend confirmation filters to be effective; performs best in trending, directional markets

### Volatility Breakout — MACD + Bollinger Band Squeeze

- **Entry:** Bollinger Bands in a squeeze state (low volatility compression), confirmed by MACD histogram turning positive
- **Exit:** MACD histogram turns negative
- **Rationale:** Captures regime transitions from low to high volatility; represents a distinct strategy family from the other two

---

## Environment Variables

The backend requires a `.env` file at `backend/.env`. Create this file before running the server.

```bash
# backend/.env

COHERE_API_KEY=your_cohere_api_key_here
FINNHUB_API_KEY=your_finnhub_api_key_here
```

| Variable | Required | Used by |
|---|---|---|
| `COHERE_API_KEY` | Yes (for Pro/Advanced features) | AI Insights, Market Intelligence summary, Strategy Generation |
| `FINNHUB_API_KEY` | Yes (for Market Intelligence) | News feed in Market Intelligence tab |

> Without these keys, the backtester and Free tier features will still work. Pro/Advanced AI features will return a graceful error message.

---

## Installation & Setup

### Prerequisites

- Python 3.10 or higher
- Git

### Step 1 — Clone the repository

```bash
git clone https://github.com/vivyanliew/is4228.git
cd is4228
```

### Step 2 — Set up the backend

```bash
cd backend
```

Create and activate a virtual environment:

**Mac / Linux**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (Command Prompt)**
```bash
python -m venv venv
venv\Scripts\activate
```

**Windows (PowerShell)**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

> If PowerShell blocks activation, run `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` as administrator first.

Install backend dependencies:

```bash
pip install -r requirements.txt
```

### Step 3 — Configure environment variables

Create `backend/.env` and add your API keys as shown in the [Environment Variables](#environment-variables) section above.

### Step 4 — Set up the frontend

Open a second terminal from the project root:

```bash
cd frontend
pip install -r requirements.txt
pip install markdown  # Required for AI Insights rendering
```

---

## How to Run the Project

Both servers must be running simultaneously. Use two separate terminals.

### Terminal 1 — Start the backend

```bash
cd backend
# Activate your virtual environment first (see above)
uvicorn app.main:app --reload
```

Verify the backend is running by opening:
- `http://127.0.0.1:8000/` — health check message
- `http://127.0.0.1:8000/docs` — interactive Swagger API documentation

### Terminal 2 — Start the frontend

```bash
cd frontend
streamlit run app.py
```

The Streamlit app will open automatically at `http://localhost:8501`.

### Using the application

1. Select a **tier** from the top-right toggle (Free / Pro / Advanced)
2. In the **Backtester** tab, select assets, date range, strategy, and parameters from the sidebar
3. Click **Run Backtest** to simulate and view results
4. On Pro tier: click **Run Risk Analysis** and **Generate AI Insights** for extended analysis
5. On Pro tier: use the **Market Intelligence** tab to research individual tickers
6. On Advanced tier: use the **Strategy Generation** tab for the full automated pipeline

---

## API Reference

The FastAPI backend exposes the following key endpoints (full documentation at `/docs`):

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/backtest/run-portfolio` | Run multi-asset portfolio backtest |
| `POST` | `/backtest/risk-analysis` | Run IS/OOS overfitting analysis |
| `POST` | `/backtest/ai-insights` | Generate AI insights via Cohere |
| `POST` | `/market-intel` | Fetch news, sentiment, AI summary for a ticker |
| `POST` | `/strategy-generation/run` | Run full multi-agent strategy generation pipeline |
| `POST` | `/agent/market-context` | Analyze market regime for a ticker |
| `POST` | `/agent/backtest` | Agent-driven backtesting |
| `POST` | `/agent/optimize` | Parameter optimization |
| `POST` | `/agent/report` | Generate strategy research report |

---
