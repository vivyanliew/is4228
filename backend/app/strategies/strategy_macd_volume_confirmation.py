import numpy as np
import pandas as pd


def run_strategy(price_df: pd.DataFrame, strategy_params: dict) -> pd.DataFrame:
    out = price_df.copy()

    macd_fast = int(strategy_params.get("macd_fast", 12))
    macd_slow = int(strategy_params.get("macd_slow", 26))
    macd_signal = int(strategy_params.get("macd_signal", 9))
    volume_ma_window = int(strategy_params.get("volume_ma_window", 20))
    volume_confirmation_ratio = float(strategy_params.get("volume_confirmation_ratio", 1.2))

    out["ema_fast"] = out["Close"].ewm(span=macd_fast, adjust=False).mean()
    out["ema_slow"] = out["Close"].ewm(span=macd_slow, adjust=False).mean()
    out["macd_line"] = out["ema_fast"] - out["ema_slow"]
    out["macd_signal"] = out["macd_line"].ewm(span=macd_signal, adjust=False).mean()
    out["volume_ma"] = out["Volume"].rolling(volume_ma_window).mean()
    out["volume_confirmed"] = out["Volume"] >= out["volume_ma"] * volume_confirmation_ratio

    out["buy_signal"] = (
        (out["macd_line"] > out["macd_signal"])
        & (out["macd_line"].shift(1) <= out["macd_signal"].shift(1))
        & out["volume_confirmed"]
    )
    out["sell_signal"] = (
        (out["macd_line"] < out["macd_signal"])
        & (out["macd_line"].shift(1) >= out["macd_signal"].shift(1))
    )

    out["position"] = 0
    in_position = False
    for idx in out.index:
        if out.at[idx, "buy_signal"] and not in_position:
            in_position = True
        elif out.at[idx, "sell_signal"] and in_position:
            in_position = False
        out.at[idx, "position"] = int(in_position)

    out["buy_marker"] = np.where(out["buy_signal"], out["Close"], np.nan)
    out["sell_marker"] = np.where(out["sell_signal"], out["Close"], np.nan)
    return out
