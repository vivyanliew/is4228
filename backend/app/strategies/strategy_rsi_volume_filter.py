import numpy as np
import pandas as pd


def _compute_rsi(series: pd.Series, window: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(window=window).mean()
    loss = (-delta.clip(upper=0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def run_strategy(price_df: pd.DataFrame, strategy_params: dict) -> pd.DataFrame:
    out = price_df.copy()

    rsi_window = int(strategy_params.get("rsi_window", 14))
    rsi_entry = float(strategy_params.get("rsi_entry", 30))
    rsi_exit = float(strategy_params.get("rsi_exit", 70))
    volume_ma_window = int(strategy_params.get("volume_ma_window", 20))
    volume_confirmation_ratio = float(strategy_params.get("volume_confirmation_ratio", 1.1))

    out["rsi"] = _compute_rsi(out["Close"], rsi_window)
    out["volume_ma"] = out["Volume"].rolling(volume_ma_window).mean()
    out["volume_confirmed"] = out["Volume"] >= out["volume_ma"] * volume_confirmation_ratio

    out["buy_signal"] = (out["rsi"] <= rsi_entry) & out["volume_confirmed"]
    out["sell_signal"] = out["rsi"] >= rsi_exit

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
