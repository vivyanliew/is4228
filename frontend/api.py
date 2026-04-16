BASE_API_URL = "http://127.0.0.1:8000"
BASE_BACKTEST_URL = f"{BASE_API_URL}/backtest"
MARKET_INTEL_URL = f"{BASE_API_URL}/market-intel"
STRATEGY_GENERATION_URL = f"{BASE_API_URL}/strategy-generation/run"
AGENT_MARKET_CONTEXT_URL = f"{BASE_API_URL}/agent/market-context"
AGENT_BACKTEST_URL = f"{BASE_API_URL}/agent/backtest"
RISK_ANALYSIS_URL = f"{BASE_BACKTEST_URL}/risk-analysis"
AI_INSIGHTS_URL = f"{BASE_BACKTEST_URL}/ai-insights"


def normalize_strategy_name(strategy: str) -> str:
    aliases = {
        "trend": "trend_follower",
    }
    return aliases.get(strategy, strategy)


def get_backtest_endpoint(strategy: str, assets: list[str]) -> str:
    normalized_strategy = normalize_strategy_name(strategy)
    strategy_registry = {
        "mean_reversion": f"{BASE_BACKTEST_URL}/run-portfolio",
        "trend_follower": f"{BASE_BACKTEST_URL}/run-portfolio",
        "macd": f"{BASE_BACKTEST_URL}/run-portfolio",
    }
    return strategy_registry[normalized_strategy]


def build_payload(config):
    strategy = normalize_strategy_name(config["strategy"])
    params = config["params"]

    # Base payload
    payload = {
        "tickers": config["assets"],
        "start_date": str(config["start_date"]),
        "end_date": str(config["end_date"]),
        "initial_capital": params.get("initial_capital", 10000),
        "strategy_name": strategy,
        "strategy_params": {}
    }

    # Strategy-specific mapping
    if strategy == "mean_reversion":
        payload["strategy_params"] = {
            "rsi_window": 14,
            "rsi_entry": params["rsi_low"],
            "rsi_exit": params["rsi_high"],
            "bb_window": params["bb_window"],
            "bb_std": params.get("bb_std", 2.0)
        }

    elif strategy == "trend_follower":
        payload["strategy_params"] = {
            "ema_fast": params["ema_short"],
            "ema_slow": params["ema_long"],
            "adx_threshold": params["adx_threshold"],
            "adx_window": int(14) #placeholders, edit accordingly when sidebar includes these
        }

    elif strategy == "macd":
        payload["strategy_params"] = {
            "macd_fast": params["macd_fast"],
            "macd_slow": params["macd_slow"],
            # "bb_width": params["bb_width"],
            "macd_signal": int(9),   #placeholders, edit accordingly when sidebar includes these
            "bb_window": int(20),
            "bb_std": float(2),
            "squeeze_quantile_window": int(20),
            "squeeze_threshold_quantile": float(0.2)
        }

    # Optional fields
    if "transaction_cost" in params:
        payload["transaction_cost"] = params["transaction_cost"]

    return payload
