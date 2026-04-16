import numpy as np
import pandas as pd


def _compute_rsi(series: pd.Series, window: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(window=window).mean()
    loss = (-delta.clip(upper=0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _compute_adx(df: pd.DataFrame, window: int) -> pd.Series:
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift(1)).abs()
    low_close = (df["Low"] - df["Close"].shift(1)).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

    plus_dm = df["High"].diff()
    minus_dm = -df["Low"].diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    atr = true_range.rolling(window=window).mean()
    plus_di = 100 * (plus_dm.rolling(window=window).mean() / atr.replace(0, np.nan))
    minus_di = 100 * (minus_dm.rolling(window=window).mean() / atr.replace(0, np.nan))
    dx = ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)) * 100
    return dx.rolling(window=window).mean()


def run_strategy(price_df: pd.DataFrame, strategy_params: dict) -> pd.DataFrame:
    out = price_df.copy()

    bb_window = int(strategy_params.get("bb_window", 20))
    bb_std = float(strategy_params.get("bb_std", 2.0))
    rsi_window = int(strategy_params.get("rsi_window", 14))
    rsi_entry = float(strategy_params.get("rsi_entry", 30))
    rsi_exit = float(strategy_params.get("rsi_exit", 65))
    adx_window = int(strategy_params.get("adx_window", 14))
    adx_threshold = float(strategy_params.get("adx_threshold", 18.0))

    out["bb_mid"] = out["Close"].rolling(bb_window).mean()
    rolling_std = out["Close"].rolling(bb_window).std()
    out["bb_upper"] = out["bb_mid"] + bb_std * rolling_std
    out["bb_lower"] = out["bb_mid"] - bb_std * rolling_std
    out["rsi"] = _compute_rsi(out["Close"], rsi_window)
    out["adx"] = _compute_adx(out, adx_window)

    out["buy_signal"] = (
        (out["Close"] <= out["bb_lower"])
        & (out["rsi"] <= rsi_entry)
        & (out["adx"] <= adx_threshold)
    )
    out["sell_signal"] = (out["Close"] >= out["bb_mid"]) | (out["rsi"] >= rsi_exit)

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
