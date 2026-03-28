import numpy as np
import pandas as pd


def add_indicators(
    df: pd.DataFrame,
    ema_fast: int = 20,
    ema_slow: int = 50,
    adx_window: int = 14,
    adx_threshold: float = 25.0,
) -> pd.DataFrame:
    out = df.copy()

    high = out["High"]
    low = out["Low"]
    close = out["Close"]

    out["ema_fast"] = close.ewm(span=ema_fast, adjust=False).mean()
    out["ema_slow"] = close.ewm(span=ema_slow, adjust=False).mean()

    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_close = close.shift(1)

    true_range = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    plus_dm = np.where(
        ((high - prev_high) > (prev_low - low)) & ((high - prev_high) > 0),
        high - prev_high,
        0.0,
    )
    minus_dm = np.where(
        ((prev_low - low) > (high - prev_high)) & ((prev_low - low) > 0),
        prev_low - low,
        0.0,
    )

    tr_smooth = true_range.ewm(alpha=1 / adx_window, adjust=False).mean()
    plus_dm_smooth = pd.Series(plus_dm, index=out.index).ewm(
        alpha=1 / adx_window, adjust=False
    ).mean()
    minus_dm_smooth = pd.Series(minus_dm, index=out.index).ewm(
        alpha=1 / adx_window, adjust=False
    ).mean()

    out["plus_di"] = 100 * plus_dm_smooth / tr_smooth.replace(0, np.nan)
    out["minus_di"] = 100 * minus_dm_smooth / tr_smooth.replace(0, np.nan)

    di_sum = (out["plus_di"] + out["minus_di"]).replace(0, np.nan)
    out["dx"] = 100 * (out["plus_di"] - out["minus_di"]).abs() / di_sum
    out["adx"] = out["dx"].ewm(alpha=1 / adx_window, adjust=False).mean()
    out["adx_threshold"] = float(adx_threshold)

    return out


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    out["ema_cross_up"] = (out["ema_fast"] > out["ema_slow"]) & (
        out["ema_fast"].shift(1) <= out["ema_slow"].shift(1)
    )
    out["ema_cross_down"] = (out["ema_fast"] < out["ema_slow"]) & (
        out["ema_fast"].shift(1) >= out["ema_slow"].shift(1)
    )

    out["trend_confirmed"] = out["adx"] > out["adx_threshold"]

    out["buy_signal"] = out["ema_cross_up"] & out["trend_confirmed"]
    out["sell_signal"] = out["ema_cross_down"]

    position = []
    current_position = 0

    for _, row in out.iterrows():
        if current_position == 0 and row["buy_signal"]:
            current_position = 1
        elif current_position == 1 and row["sell_signal"]:
            current_position = 0

        position.append(current_position)

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

    out = out.dropna(
        subset=["ema_fast", "ema_slow", "plus_di", "minus_di", "adx"]
    ).copy()

    return out


def run_strategy(price_df: pd.DataFrame, strategy_params: dict) -> pd.DataFrame:
    out = add_indicators(price_df, **strategy_params)
    out = generate_signals(out)
    return out
