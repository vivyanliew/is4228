def build_payload(config):
    strategy = config["strategy"]
    params = config["params"]

    # Base payload
    payload = {
        "tickers": config["assets"], #to change when we allow for more edits
        "start_date": str(config["start_date"]),
        "end_date": str(config["end_date"]),
        "initial_capital": params.get("initial_capital", 10000),
        "strategy_name": strategy,
        "strategy_params": {}
    }

    # Strategy-specific mapping
    if strategy == "mean_reversion":
        payload["strategy_params"] = {
            "rsi_window": 14,  # you can expose later
            "rsi_entry": params["rsi_low"],
            "rsi_exit": params["rsi_high"],
            "bb_window": params["bb_window"],
            "bb_std": 2.0  # default (or expose later)
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
