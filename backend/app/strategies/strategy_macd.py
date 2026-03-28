import numpy as np
import pandas as pd


def add_indicators(
    df: pd.DataFrame,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    bb_window: int = 20,
    bb_std: float = 2.0,
    squeeze_quantile_window: int = 20,
    squeeze_threshold_quantile: float = 0.2,
) -> pd.DataFrame:
    out = df.copy()

    close = out["Close"]

    # MACD
    out["ema_fast"] = close.ewm(span=macd_fast, adjust=False).mean()
    out["ema_slow"] = close.ewm(span=macd_slow, adjust=False).mean()
    out["macd_line"] = out["ema_fast"] - out["ema_slow"]
    out["macd_signal"] = out["macd_line"].ewm(span=macd_signal, adjust=False).mean()
    out["macd_hist"] = out["macd_line"] - out["macd_signal"]

    # Bollinger Bands
    out["bb_mid"] = close.rolling(window=bb_window).mean()
    out["bb_std"] = close.rolling(window=bb_window).std()
    out["bb_upper"] = out["bb_mid"] + bb_std * out["bb_std"]
    out["bb_lower"] = out["bb_mid"] - bb_std * out["bb_std"]

    # Bollinger Band width
    out["bb_width"] = (out["bb_upper"] - out["bb_lower"]) / out["bb_mid"]

    # Rolling squeeze threshold
    out["bb_width_threshold"] = out["bb_width"].rolling(
        window=squeeze_quantile_window
    ).quantile(squeeze_threshold_quantile)

    out["is_squeeze"] = out["bb_width"] <= out["bb_width_threshold"]

    return out


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    # MACD histogram crossovers
    out["macd_cross_up"] = (out["macd_hist"] > 0) & (out["macd_hist"].shift(1) <= 0)
    out["macd_cross_down"] = (out["macd_hist"] < 0) & (out["macd_hist"].shift(1) >= 0)

    # Buy / sell logic
    out["buy_signal"] = out["is_squeeze"] & out["macd_cross_up"]
    out["sell_signal"] = out["macd_cross_down"]

    # Build position path
    position = []
    current_position = 0

    for _, row in out.iterrows():
        if current_position == 0 and row["buy_signal"]:
            current_position = 1
        elif current_position == 1 and row["sell_signal"]:
            current_position = 0

        position.append(current_position)

    out["position"] = position

    # Plot markers
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

    # Drop rows before indicators are ready
    required_cols = [
        "macd_line",
        "macd_signal",
        "macd_hist",
        "bb_mid",
        "bb_upper",
        "bb_lower",
        "bb_width",
        "bb_width_threshold",
    ]
    out = out.dropna(subset=required_cols).copy()

    return out


def run_strategy(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    out = add_indicators(df, **params)
    out = generate_signals(out)
    return out