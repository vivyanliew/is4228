import pandas as pd

from app.utils import (
    fetch_price_data,
    run_strategy_by_name,
    add_backtest_columns,
    build_trade_records,
    calculate_metrics,
)


class BacktestAgent:
    """
    Runs a walk-forward backtest, splitting historical data into
    in-sample (IS) and out-of-sample (OOS) windows.

    The IS window is used to represent the 'training' period;
    the OOS window is the held-out validation period.
    Both windows use the same fixed parameters — no fitting happens here.
    The split prevents look-ahead when the OptimizationAgent selects params.
    """

    def run(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        strategy_name: str,
        strategy_params: dict,
        initial_capital: float = 10000.0,
        is_split: float = 0.7,
    ) -> dict:
        price_df = fetch_price_data(ticker, start_date, end_date)

        if len(price_df) < 60:
            raise ValueError(
                f"Insufficient data for {ticker}: only {len(price_df)} rows. Need at least 60."
            )

        split_idx = int(len(price_df) * is_split)

        df_is = price_df.iloc[:split_idx].copy().reset_index(drop=True)
        df_oos = price_df.iloc[split_idx:].copy().reset_index(drop=True)

        is_result = self._run_on_window(df_is, strategy_name, strategy_params, initial_capital)
        oos_result = self._run_on_window(df_oos, strategy_name, strategy_params, initial_capital)

        return {
            "is": is_result,
            "oos": oos_result,
            "is_end_date": str(df_is["Date"].iloc[-1].date()),
            "oos_start_date": str(df_oos["Date"].iloc[0].date()),
        }

    def _run_on_window(
        self,
        df: pd.DataFrame,
        strategy_name: str,
        strategy_params: dict,
        capital: float,
    ) -> dict:
        signal_df = run_strategy_by_name(strategy_name, df, strategy_params)
        signal_df = add_backtest_columns(signal_df, capital)
        trades = build_trade_records(signal_df)
        metrics = calculate_metrics(signal_df, trades, capital)
        return {"metrics": metrics, "trades": trades}
