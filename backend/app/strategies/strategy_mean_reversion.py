import numpy as np
import pandas as pd


def compute_rsi(series: pd.Series, window: int = 14) -> pd.Series:
    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window=window, min_periods=window).mean()
    avg_loss = loss.rolling(window=window, min_periods=window).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    return rsi


def run_strategy(price_df: pd.DataFrame, strategy_params: dict) -> pd.DataFrame:
    out = price_df.copy()

    bb_window = strategy_params.get("bb_window", 20)
    bb_std = strategy_params.get("bb_std", 2.0)
    rsi_window = strategy_params.get("rsi_window", 14)
    rsi_entry = strategy_params.get("rsi_entry", 30)
    rsi_exit = strategy_params.get("rsi_exit", 70)

    out["bb_mid"] = out["Close"].rolling(bb_window).mean()
    rolling_std = out["Close"].rolling(bb_window).std()

    out["bb_upper"] = out["bb_mid"] + bb_std * rolling_std
    out["bb_lower"] = out["bb_mid"] - bb_std * rolling_std

    out["rsi"] = compute_rsi(out["Close"], window=rsi_window)

    out["buy_signal"] = (
        (out["Close"] <= out["bb_lower"]) &
        (out["rsi"] < rsi_entry)
    )

    out["sell_signal"] = (
        (out["Close"] >= out["bb_upper"]) |
        (out["rsi"] > rsi_exit)
    )

    position = []
    in_position = 0

    for _, row in out.iterrows():
        if in_position == 0 and row["buy_signal"]:
            in_position = 1
        elif in_position == 1 and row["sell_signal"]:
            in_position = 0

        position.append(in_position)

    out["position"] = position
    prev_position = out["position"].shift(1).fillna(0)
    out["buy_marker"] = np.where(
        (out["position"] == 1) & (prev_position == 0),
        out["Close"],
        np.nan,
    )
    out["sell_marker"] = np.where(
        (out["position"] == 0) & (prev_position == 1),
        out["Close"],
        np.nan,
    )

    return out