import numpy as np
import pandas as pd
from typing import List, Dict, Union


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
    # Allow entry if a squeeze occurred within the last 5 bars
    out["recent_squeeze"] = out["is_squeeze"].rolling(window=5, min_periods=1).max().astype(bool)
    out["buy_signal"] = out["recent_squeeze"] & out["macd_cross_up"]
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


def run_strategy_multi_ticker(
    price_dfs: Dict[str, pd.DataFrame],
    params: dict
) -> pd.DataFrame:
    """
    Run MACD strategy on multiple tickers with equal weighting.
    
    Args:
        price_dfs: Dictionary mapping ticker symbols to their price dataframes
        params: Strategy parameters (macd_fast, macd_slow, etc.)
    
    Returns:
        Combined dataframe with equal-weighted positions and signals
    """
    if not price_dfs:
        raise ValueError("At least one ticker must be provided.")
    
    tickers = list(price_dfs.keys())
    num_tickers = len(tickers)
    weight = 1.0 / num_tickers
    
    # Run strategy on each ticker
    strategy_results = {}
    for ticker, price_df in price_dfs.items():
        strategy_results[ticker] = run_strategy(price_df, params)
    
    # Merge all dataframes by Date
    merged_df = None
    for ticker in tickers:
        df = strategy_results[ticker][["Date", "Close", "position"]].copy()
        df = df.rename(columns={
            "Close": f"close_{ticker}",
            "position": f"position_{ticker}"
        })
        
        if merged_df is None:
            merged_df = df
        else:
            merged_df = pd.merge(merged_df, df, on="Date", how="inner")
    
    # Calculate equal-weighted portfolio position (average of all positions)
    position_cols = [f"position_{ticker}" for ticker in tickers]
    merged_df["position"] = merged_df[position_cols].mean(axis=1)
    
    # Threshold: if average position >= 0.5, consider it as position=1, else 0
    merged_df["position"] = (merged_df["position"] >= 0.5).astype(int)
    
    # Calculate weighted close price
    close_cols = [f"close_{ticker}" for ticker in tickers]
    merged_df["Close"] = merged_df[close_cols].mean(axis=1)
    
    # Generate buy/sell markers based on position changes
    prev_position = merged_df["position"].shift(1).fillna(0)
    
    merged_df["buy_marker"] = np.where(
        (merged_df["position"] == 1) & (prev_position == 0),
        merged_df["Close"],
        np.nan,
    )
    
    merged_df["sell_marker"] = np.where(
        (merged_df["position"] == 0) & (prev_position == 1),
        merged_df["Close"],
        np.nan,
    )
    
    return merged_df