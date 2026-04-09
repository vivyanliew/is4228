class RiskAgent:
    """
    Evaluates backtest results for overfitting and statistical validity.

    Overfitting score (0 = clean, 3 = high risk):
      +1  OOS trade count below minimum
      +1  Sharpe ratio decays more than threshold from IS to OOS
      +1  OOS cumulative return is negative
    """

    MIN_OOS_TRADES = 20
    SHARPE_DECAY_THRESHOLD = 0.7  # OOS Sharpe must be >= 70% of IS Sharpe

    def evaluate(self, backtest_result: dict) -> dict:
        is_metrics = backtest_result["is"]["metrics"]
        oos_metrics = backtest_result["oos"]["metrics"]

        flags = []
        overfitting_score = 0

        # --- 1. Minimum OOS trade count ---
        oos_trade_count = oos_metrics.get("number_of_trades", 0)
        if oos_trade_count < self.MIN_OOS_TRADES:
            flags.append(
                f"Low OOS trade count: {oos_trade_count} trades "
                f"(minimum {self.MIN_OOS_TRADES} required for statistical significance)"
            )
            overfitting_score += 1

        # --- 2. Sharpe decay ---
        is_sharpe = is_metrics.get("sharpe_ratio")
        oos_sharpe = oos_metrics.get("sharpe_ratio")
        sharpe_decay_ratio = None

        if is_sharpe is not None and is_sharpe > 0:
            if oos_sharpe is None:
                flags.append(
                    "OOS Sharpe is None — strategy produced no trades in the OOS window"
                )
                overfitting_score += 1
            else:
                sharpe_decay_ratio = round(oos_sharpe / is_sharpe, 4)
                if sharpe_decay_ratio < self.SHARPE_DECAY_THRESHOLD:
                    flags.append(
                        f"Sharpe decay: OOS/IS ratio = {sharpe_decay_ratio:.2f} "
                        f"(threshold {self.SHARPE_DECAY_THRESHOLD}) — possible overfitting"
                    )
                    overfitting_score += 1

        # --- 3. OOS profitability ---
        oos_cum_ret = oos_metrics.get("cumulative_return_pct")
        if oos_cum_ret is not None and oos_cum_ret <= 0:
            flags.append(
                f"OOS cumulative return is {oos_cum_ret:.2f}% — strategy lost money on unseen data"
            )
            overfitting_score += 1

        # --- 4. Calmar ratio (OOS) ---
        oos_ann_ret = oos_metrics.get("annualized_return_pct")
        oos_max_dd = oos_metrics.get("max_drawdown_pct")
        calmar_ratio = None
        if oos_ann_ret is not None and oos_max_dd is not None and oos_max_dd != 0:
            calmar_ratio = round(oos_ann_ret / abs(oos_max_dd), 4)

        return {
            "overfitting_score": overfitting_score,
            "overfitting_label": self._label(overfitting_score),
            "flags": flags,
            "sharpe_decay_ratio": sharpe_decay_ratio,
            "calmar_ratio_oos": calmar_ratio,
            "oos_trade_count": oos_trade_count,
            "is_sharpe": is_sharpe,
            "oos_sharpe": oos_sharpe,
        }

    @staticmethod
    def _label(score: int) -> str:
        if score == 0:
            return "Low Risk"
        if score == 1:
            return "Moderate Risk"
        return "High Risk"
