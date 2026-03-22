# Browser-Based Strategy Research and Backtesting Tool

A browser-based trading strategy research and backtesting tool for novice and intermediate retail traders, as well as student quants. The platform allows users to test rule-based technical strategies on historical market data, inspect trade signals, and evaluate performance before risking real capital.

## Quick Setup Checklist

1. **Clone the repository** and open the project folder
2. **Set up the backend environment** by creating and activating a Python virtual environment
3. **Install backend dependencies** from `requirements.txt`
4. **Run the FastAPI server** and verify the local API is working
5. **Open Swagger docs** to confirm the backend is ready for development

## Key Capabilities

- **Strategy testing**: Backtest rule-based technical strategies on historical data
- **Multiple strategy types**: Mean Reversion, Trend Following, and Volatility Breakout
- **Metrics output**: Inspect returns, trade logs, and risk metrics
- **API-first backend**: Built with FastAPI for frontend integration
- **Extensible design**: Structured to support more assets, indicators, and strategy parameters later

## Repository Layout

- `backend/` — Python backend for API and strategy execution
- `backend/app/main.py` — FastAPI application entry point
- `backend/app/models.py` — request and response models
- `backend/requirements.txt` — backend Python dependencies

## Current Project Scope

For the current proof of concept, the team is focusing on:

- Python backend
- FastAPI server
- historical data backtesting
- API output for strategy metrics and signals
- strategy implementation starting with Mean Reversion

## Strategies

### Strategy A: Mean Reversion (RSI + Bollinger Bands)

**Logic**
- Buy when price touches the lower Bollinger Band and RSI is below 30
- Sell when price touches the upper Bollinger Band or RSI rises above 70

**Why this strategy**
- Suitable for the beginner tier
- One of the most common strategies newer traders encounter first
- Easy to explain visually and conceptually

### Strategy B: Trend Follower (EMA Cross + ADX)

**Logic**
- Buy when the 20-period EMA crosses above the 50-period EMA
- Only enter if ADX is above 25, indicating trend strength

**Why this strategy**
- Teaches that moving average crossovers work better in trending markets
- Shows the value of adding filters instead of using signals blindly

### Strategy C: Volatility Breakout (MACD + Bollinger Band Width)

**Logic**
- Buy when Bollinger Bands are in a squeeze state
- Confirm entry when the MACD histogram turns positive

**Why this strategy**
- Captures regime shifts from low volatility to expansion
- Introduces a different strategy family from mean reversion and trend following

## Prerequisites

- Python 3.10+ recommended
- Git
- Cursor, VS Code, or another code editor

## Backend Setup

### Step 1: Clone the Repository

```bash
git clone <https://github.com/vivyanliew/is4228.git>
cd is4228
```

### Step 2: Go Into the Backend Folder

```bash
cd backend
```

### Step 3: Create a Virtual Environment

#### Mac / Linux

```bash
python3 -m venv venv
```

#### Windows

```bash
python -m venv venv
```

If `python` does not work on Windows, try:

```bash
py -m venv venv
```

### Step 4: Activate the Virtual Environment

#### Mac / Linux

```bash
source venv/bin/activate
```

#### Windows Command Prompt

```bash
venv\Scripts\activate
```

#### Windows PowerShell

```powershell
venv\Scripts\Activate.ps1
```

After activation, your terminal should show something like `(venv)` at the front.

### Step 5: Install Dependencies (modify requirements as needed for frontend)

```bash
pip install -r requirements.txt
```

If `pip` does not work, try:

```bash
python -m pip install -r requirements.txt
```

or on some Windows machines:

```bash
py -m pip install -r requirements.txt
```

### Step 6: Run the Backend Server

```bash
uvicorn app.main:app --reload
```

If that does not work, try:

```bash
python -m uvicorn app.main:app --reload
```

### Step 7: Verify That the Server Is Working

Open these in your browser:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

Expected results:

- `/` returns a message saying the backend is running
- `/health` returns a status response
- `/docs` opens the FastAPI Swagger UI

### Exit the Virtual Environment

When you are done working, you can deactivate the virtual environment by running:

```bash
deactivate

## Current Backend Files

### `backend/requirements.txt`

```txt
fastapi
uvicorn[standard]
pandas
numpy
yfinance
pydantic
```

### `backend/app/main.py`

```python
from fastapi import FastAPI

app = FastAPI(title="Backtesting API")


@app.get("/")
def root():
    return {"message": "Backend is running"}


@app.get("/health")
def health():
    return {"status": "ok"}
```

## Development Workflow

### Recommended Git Workflow

Before starting work:

```bash
git pull origin main
git checkout -b your-branch-name
```

After making changes:

```bash
git add .
git commit -m "Describe your changes"
git push origin your-branch-name
```

### Suggested Team Workflow

1. Pull the latest version of `main`
2. Set up the backend locally
3. Confirm the server and docs page load successfully
4. Work on feature branches instead of directly on `main`
5. Open pull requests or send branches for review before merging


## Common Issues

### `python` not found

Try:

#### Mac / Linux

```bash
python3 -m venv venv
```

#### Windows

```bash
py -m venv venv
```

### `pip` not found

Try:

```bash
python -m pip install -r requirements.txt
```

or:

```bash
py -m pip install -r requirements.txt
```

### PowerShell blocks activation on Windows

If you get an execution policy error, use Command Prompt instead:

```bash
venv\Scripts\activate
```

Or run this in PowerShell as administrator:

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then try again:

```powershell
venv\Scripts\Activate.ps1
```

### `uvicorn` not recognized

Try:

```bash
python -m uvicorn app.main:app --reload
```

### Port 8000 already in use

Run on a different port:

```bash
uvicorn app.main:app --reload --port 8001
```

Then open:

- `http://127.0.0.1:8001/docs`

## Notes for Teammates

After setup, please confirm that:

- the virtual environment works
- dependencies installed successfully
- the backend server starts
- `/docs` loads in the browser



