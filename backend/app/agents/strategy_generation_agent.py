import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import cohere

from app.agents.strategy_spec import StrategySpec


SUPPORTED_STRATEGIES = {
    "macd",
    "mean_reversion",
    "trend_follower",
    "macd_volume_confirmation",
    "rsi_adx_filter",
    "rsi_volume_filter",
}
EXPERIMENTAL_STRATEGIES = {
    "rsi_adx_filter",
    "rsi_volume_filter",
    "macd_volume_confirmation",
}

DEFAULT_PARAM_SETS = {
    "macd": {
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "bb_window": 20,
        "bb_std": 2.0,
        "squeeze_quantile_window": 20,
        "squeeze_threshold_quantile": 0.2,
    },
    "mean_reversion": {
        "bb_window": 20,
        "bb_std": 2.0,
        "rsi_window": 14,
        "rsi_entry": 30,
        "rsi_exit": 70,
    },
    "trend_follower": {
        "ema_fast": 20,
        "ema_slow": 50,
        "adx_window": 14,
        "adx_threshold": 25.0,
    },
    "macd_volume_confirmation": {
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "volume_ma_window": 20,
        "volume_confirmation_ratio": 1.2,
    },
    "rsi_adx_filter": {
        "bb_window": 20,
        "bb_std": 2.0,
        "rsi_window": 14,
        "rsi_entry": 30,
        "rsi_exit": 65,
        "adx_window": 14,
        "adx_threshold": 18.0,
    },
    "rsi_volume_filter": {
        "rsi_window": 14,
        "rsi_entry": 30,
        "rsi_exit": 70,
        "volume_ma_window": 20,
        "volume_confirmation_ratio": 1.1,
    },
}

STRATEGY_ALIASES = {
    "ema": "trend_follower",
    "trend": "trend_follower",
    "trend_following": "trend_follower",
    "trend_follower": "trend_follower",
    "macd": "macd",
    "mean_reversion": "mean_reversion",
    "mean reversion": "mean_reversion",
    "rsi_adx_filter": "rsi_adx_filter",
    "rsi_volume_filter": "rsi_volume_filter",
    "macd_volume_confirmation": "macd_volume_confirmation",
}

PARAM_ALIASES = {
    "macd": {"fast": "macd_fast", "slow": "macd_slow", "signal": "macd_signal"},
    "mean_reversion": {"rsi_period": "rsi_window"},
    "trend_follower": {"fast": "ema_fast", "slow": "ema_slow"},
}

QUALITY_SCORE = {"low": 0.55, "medium": 0.72, "high": 0.88}


class StrategyGenerationAgent:
    """
    Agent 2 pipeline:
    1. Retrieve relevant research entries.
    2. Build grounded generation context from market context + research.
    3. Ask Cohere for structured strategy candidates when enabled.
    4. Fall back to deterministic rule-based generation when needed.
    5. Normalize, validate, tag research basis, and separate backtestable vs experimental ideas.
    """

    def __init__(
        self,
        cohere_api_key: Optional[str] = None,
        model: str = "command-a-03-2025",
        research_path: Optional[Path] = None,
    ) -> None:
        self.model = model
        api_key = cohere_api_key or os.getenv("COHERE_API_KEY")
        self.client = cohere.Client(api_key) if api_key else None
        self.research_path = research_path or Path(__file__).resolve().parents[1] / "research" / "paper_index.json"
        self.research_index = self._load_research_index()

    def generate(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        market_context: Dict[str, Any],
        max_candidates: int = 3,
        use_llm: bool = True,
        allow_experimental: bool = True,
    ) -> List[StrategySpec]:
        research_entries = self._retrieve_research_context(market_context, allow_experimental)

        if use_llm and self.client is not None:
            llm_specs = self._generate_with_llm(
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
                market_context=market_context,
                research_entries=research_entries,
                max_candidates=max_candidates,
                allow_experimental=allow_experimental,
            )
            if llm_specs:
                return self._finalize_specs(
                    llm_specs,
                    ticker=ticker,
                    start_date=start_date,
                    end_date=end_date,
                    market_context=market_context,
                    research_entries=research_entries,
                    max_candidates=max_candidates,
                    allow_experimental=allow_experimental,
                )

        rule_specs = self._generate_rule_based(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            market_context=market_context,
            research_entries=research_entries,
            allow_experimental=allow_experimental,
        )
        return self._finalize_specs(
            rule_specs,
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            market_context=market_context,
            research_entries=research_entries,
            max_candidates=max_candidates,
            allow_experimental=allow_experimental,
        )

    def _load_research_index(self) -> Dict[str, Any]:
        try:
            with self.research_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, dict):
                return {"papers": []}
            papers = data.get("papers", [])
            data["papers"] = self._flatten_papers(papers)
            return data
        except Exception:
            return {"papers": []}

    def _flatten_papers(self, papers: Any) -> List[Dict[str, Any]]:
        flattened: List[Dict[str, Any]] = []
        if not isinstance(papers, list):
            return flattened
        for item in papers:
            if isinstance(item, dict):
                flattened.append(item)
            elif isinstance(item, list):
                flattened.extend(self._flatten_papers(item))
        return flattened

    def _retrieve_research_context(
        self,
        market_context: Dict[str, Any],
        allow_experimental: bool,
    ) -> List[Dict[str, Any]]:
        papers = self.research_index.get("papers", [])
        bias = str(market_context.get("strategy_bias", "neutral")).lower()
        preferred_families = self._preferred_families_for_bias(bias)
        if allow_experimental:
            preferred_families.add("experimental")

        selected: List[Dict[str, Any]] = []
        for paper in papers:
            families = set(paper.get("strategy_family", []))
            if families & preferred_families:
                selected.append(paper)

        if not selected:
            selected = papers[:3]
        return selected[:3]

    def _preferred_families_for_bias(self, bias: str) -> set[str]:
        if bias == "momentum":
            return {"macd", "trend_follower"}
        if bias == "mean_reversion":
            return {"mean_reversion"}
        return {"macd", "trend_follower", "mean_reversion"}

    def _generate_with_llm(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        market_context: Dict[str, Any],
        research_entries: List[Dict[str, Any]],
        max_candidates: int,
        allow_experimental: bool,
    ) -> List[StrategySpec]:
        prompt = self._build_prompt(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            market_context=market_context,
            research_entries=research_entries,
            max_candidates=max_candidates,
            allow_experimental=allow_experimental,
        )
        try:
            response = self.client.chat(model=self.model, message=prompt)
            raw_text = getattr(response, "text", "") or ""
            return self._parse_llm_output(raw_text)
        except Exception:
            return []

    def _build_prompt(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        market_context: Dict[str, Any],
        research_entries: List[Dict[str, Any]],
        max_candidates: int,
        allow_experimental: bool,
    ) -> str:
        evidence = []
        for entry in research_entries:
            evidence.append(
                {
                    "id": entry.get("id"),
                    "strategy_family": entry.get("strategy_family", []),
                    "summary": entry.get("summary", ""),
                    "key_findings": entry.get("key_findings", [])[:2],
                    "parameter_guidance": entry.get("parameter_guidance", {}),
                }
            )

        experimental_instruction = (
            "You may propose research-enhanced strategies only if they match one of the supported live engine families listed below."
            if allow_experimental
            else
            "Only return backtestable strategies supported by the current live engine."
        )

        return (
            "You are Agent 2, a research-grounded quantitative strategy generation assistant.\n"
            "Use the market context and research evidence below to propose strategy candidates.\n"
            "Do not invent unsupported claims. Ground each candidate in the provided evidence.\n"
            f"{experimental_instruction}\n"
            "Return valid JSON only with schema:\n"
            "{\n"
            '  "strategies": [\n'
            "    {\n"
            '      "strategy_name": "string",\n'
            '      "strategy_params": {"param": "value"},\n'
            '      "description": "short description",\n'
            '      "rationale": "why this fits the regime",\n'
            '      "research_basis": ["paper_id_1"],\n'
            '      "backtestable": true,\n'
            '      "confidence": 0.0,\n'
            '      "implementation_hint": "optional"\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "Live engine strategy families and parameter names:\n"
            "- macd: macd_fast, macd_slow, macd_signal, bb_window, bb_std, squeeze_quantile_window, squeeze_threshold_quantile\n"
            "- mean_reversion: bb_window, bb_std, rsi_window, rsi_entry, rsi_exit\n"
            "- trend_follower: ema_fast, ema_slow, adx_window, adx_threshold\n"
            "- macd_volume_confirmation: macd_fast, macd_slow, macd_signal, volume_ma_window, volume_confirmation_ratio\n"
            "- rsi_adx_filter: bb_window, bb_std, rsi_window, rsi_entry, rsi_exit, adx_window, adx_threshold\n"
            "- rsi_volume_filter: rsi_window, rsi_entry, rsi_exit, volume_ma_window, volume_confirmation_ratio\n"
            "All returned strategies must be backtestable in the current live engine.\n"
            f"Ticker: {ticker}\n"
            f"Date range: {start_date} to {end_date}\n"
            f"Market context: {json.dumps(market_context, default=str)}\n"
            f"Research evidence: {json.dumps(evidence, default=str)}\n"
            f"Generate up to {max_candidates} candidates.\n"
            "Favor distinct strategies that are consistent with the regime and evidence. Keep the response concise."
        )

    def _parse_llm_output(self, raw_text: str) -> List[StrategySpec]:
        parsed = self._extract_json_object(raw_text)
        if not isinstance(parsed, dict):
            return []

        strategies = parsed.get("strategies", [])
        specs: List[StrategySpec] = []
        for item in strategies:
            if not isinstance(item, dict):
                continue

            strategy_name = self._normalize_strategy_name(item.get("strategy_name"))
            if strategy_name not in SUPPORTED_STRATEGIES:
                continue
            backtestable = True

            strategy_params = self._normalize_params(strategy_name, item.get("strategy_params", {}), backtestable)
            specs.append(
                StrategySpec(
                    strategy_name=strategy_name,
                    strategy_params=strategy_params,
                    description=item.get("description", strategy_name.replace("_", " ").title()),
                    rationale=item.get("rationale", ""),
                    source="cohere_grounded",
                    backtestable=backtestable,
                    confidence=self._clamp_confidence(item.get("confidence", 0.7)),
                    research_basis=self._coerce_string_list(item.get("research_basis", [])),
                    generated_code=item.get("generated_code"),
                    implementation_hint=item.get("implementation_hint"),
                )
            )

        return specs

    def _generate_rule_based(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        market_context: Dict[str, Any],
        research_entries: List[Dict[str, Any]],
        allow_experimental: bool,
    ) -> List[StrategySpec]:
        bias = str(market_context.get("strategy_bias", "neutral")).lower()
        volatility = self._volatility_bucket(market_context)
        trend_direction = str(market_context.get("trend_direction", "")).lower()

        if bias == "momentum":
            specs = self._momentum_specs(research_entries, volatility, trend_direction, allow_experimental)
        elif bias == "mean_reversion":
            specs = self._mean_reversion_specs(research_entries, volatility, allow_experimental)
        else:
            specs = self._neutral_specs(research_entries, volatility, trend_direction, allow_experimental)

        for spec in specs:
            spec.metadata.update(
                {
                    "ticker": ticker,
                    "start_date": start_date,
                    "end_date": end_date,
                    "market_bias": bias,
                }
            )
        return specs

    def _momentum_specs(
        self,
        research_entries: List[Dict[str, Any]],
        volatility: str,
        trend_direction: str,
        allow_experimental: bool,
    ) -> List[StrategySpec]:
        macd = DEFAULT_PARAM_SETS["macd"].copy()
        trend = DEFAULT_PARAM_SETS["trend_follower"].copy()
        if volatility == "high":
            macd["squeeze_threshold_quantile"] = 0.15
            trend["adx_threshold"] = 30.0
        elif volatility == "low":
            macd["squeeze_threshold_quantile"] = 0.25
            trend["adx_threshold"] = 22.0
        if trend_direction == "up":
            trend["ema_fast"] = 15
        elif trend_direction == "down":
            trend["ema_slow"] = 60

        specs = [
            self._make_supported_spec("macd", macd, "MACD breakout tuned for momentum regimes.", "Momentum bias favors trend continuation signals confirmed by MACD and squeeze release.", research_entries),
            self._make_supported_spec("trend_follower", trend, "EMA crossover with ADX confirmation.", "Trending regimes favor crossover signals with an explicit trend-strength filter.", research_entries),
        ]
        if allow_experimental:
            specs.append(
                self._make_research_supported_spec(
                    "macd_volume_confirmation",
                    {"macd_fast": 12, "macd_slow": 26, "macd_signal": 9, "volume_ma_window": 20, "volume_confirmation_ratio": 1.2},
                    "MACD trend-following with a volume confirmation filter.",
                    "Volume confirmation may help reduce weak breakout entries in noisy momentum regimes.",
                    research_entries,
                    related_family="macd",
                )
            )
        return specs

    def _mean_reversion_specs(
        self,
        research_entries: List[Dict[str, Any]],
        volatility: str,
        allow_experimental: bool,
    ) -> List[StrategySpec]:
        baseline = DEFAULT_PARAM_SETS["mean_reversion"].copy()
        alt = DEFAULT_PARAM_SETS["mean_reversion"].copy()
        if volatility == "high":
            baseline["bb_std"] = 2.5
            baseline["rsi_entry"] = 25
            alt["bb_window"] = 25
            alt["rsi_exit"] = 65
        elif volatility == "low":
            baseline["bb_std"] = 1.8
            alt["rsi_entry"] = 35
            alt["rsi_exit"] = 60

        specs = [
            self._make_supported_spec("mean_reversion", baseline, "Baseline Bollinger plus RSI mean-reversion setup.", "Range-bound markets favor buying weakness and exiting on normalization.", research_entries),
            self._make_supported_spec("mean_reversion", alt, "Alternative mean-reversion setup with a different sensitivity profile.", "A second reversion profile helps test whether the edge is robust to parameter changes.", research_entries),
        ]
        if allow_experimental:
            specs.append(
                self._make_research_supported_spec(
                    "rsi_adx_filter",
                    {"bb_window": 20, "bb_std": 2.0, "rsi_window": 14, "rsi_entry": 30, "rsi_exit": 65, "adx_window": 14, "adx_threshold": 18.0},
                    "RSI and Bollinger mean reversion filtered by low ADX trend strength.",
                    "ADX can help avoid forcing reversion entries when the market is still strongly trending.",
                    research_entries,
                    related_family="mean_reversion",
                )
            )
        return specs

    def _neutral_specs(
        self,
        research_entries: List[Dict[str, Any]],
        volatility: str,
        trend_direction: str,
        allow_experimental: bool,
    ) -> List[StrategySpec]:
        specs = (
            self._momentum_specs(research_entries, volatility, trend_direction, allow_experimental=False)[:1]
            + self._mean_reversion_specs(research_entries, volatility, allow_experimental=False)[:1]
            + [self._make_supported_spec("trend_follower", DEFAULT_PARAM_SETS["trend_follower"].copy(), "Balanced trend follower baseline.", "Neutral regimes benefit from testing both continuation and reversal styles.", research_entries)]
        )
        if allow_experimental:
            specs.append(
                self._make_research_supported_spec(
                    "rsi_volume_filter",
                    {"rsi_window": 14, "rsi_entry": 30, "rsi_exit": 70, "volume_ma_window": 20, "volume_confirmation_ratio": 1.1},
                    "RSI reversal setup with a volume participation filter.",
                    "A volume filter can make neutral-regime reversal entries more selective.",
                    research_entries,
                    related_family="mean_reversion",
                )
            )
        return specs

    def _make_supported_spec(self, strategy_name: str, strategy_params: Dict[str, Any], description: str, rationale: str, research_entries: List[Dict[str, Any]]) -> StrategySpec:
        research_basis = self._research_ids_for_strategy(strategy_name, research_entries)
        return StrategySpec(
            strategy_name=strategy_name,
            strategy_params=strategy_params,
            description=description,
            rationale=rationale,
            source="rule_based_research",
            backtestable=True,
            confidence=self._confidence_from_research(research_basis, research_entries, True),
            research_basis=research_basis,
            generated_code=self._generate_supported_code(strategy_name, strategy_params),
            metadata={"candidate_type": "backtestable_now"},
        )

    def _make_research_supported_spec(
        self,
        strategy_name: str,
        strategy_params: Dict[str, Any],
        description: str,
        rationale: str,
        research_entries: List[Dict[str, Any]],
        related_family: str,
    ) -> StrategySpec:
        research_basis = self._research_ids_for_strategy(related_family, research_entries)
        if not research_basis:
            research_basis = self._research_ids_for_strategy("experimental", research_entries)
        return StrategySpec(
            strategy_name=strategy_name,
            strategy_params=strategy_params,
            description=description,
            rationale=rationale,
            source="rule_based_research",
            backtestable=True,
            confidence=self._confidence_from_research(research_basis, research_entries, True),
            research_basis=research_basis,
            generated_code=self._generate_supported_code(strategy_name, strategy_params),
            implementation_hint="Supported in the current backtest engine.",
            metadata={"candidate_type": "backtestable_now", "research_variant": True},
        )

    def _finalize_specs(
        self,
        specs: List[StrategySpec],
        ticker: str,
        start_date: str,
        end_date: str,
        market_context: Dict[str, Any],
        research_entries: List[Dict[str, Any]],
        max_candidates: int,
        allow_experimental: bool,
    ) -> List[StrategySpec]:
        finalized: List[StrategySpec] = []
        for spec in self._dedupe_specs(specs):
            spec.strategy_name = self._normalize_strategy_name(spec.strategy_name)
            if spec.strategy_name not in SUPPORTED_STRATEGIES:
                continue
            spec.backtestable = True
            spec.strategy_params = self._normalize_params(spec.strategy_name, spec.strategy_params, True)
            spec.generated_code = spec.generated_code or self._generate_supported_code(spec.strategy_name, spec.strategy_params)
            if not spec.research_basis:
                spec.research_basis = self._research_ids_for_strategy(spec.strategy_name, research_entries)
            spec.confidence = self._clamp_confidence(spec.confidence or self._confidence_from_research(spec.research_basis, research_entries, spec.backtestable))
            spec.metadata.update({"ticker": ticker, "start_date": start_date, "end_date": end_date, "market_bias": market_context.get("strategy_bias", "neutral"), "regime": market_context.get("regime"), "trend_direction": market_context.get("trend_direction")})
            finalized.append(spec)
        finalized.sort(key=lambda spec: (spec.backtestable, spec.confidence), reverse=True)
        return finalized[:max_candidates]

    def _research_ids_for_strategy(self, strategy_name: str, research_entries: List[Dict[str, Any]]) -> List[str]:
        ids: List[str] = []
        for entry in research_entries:
            families = set(entry.get("strategy_family", []))
            if strategy_name in families or (strategy_name == "experimental" and "experimental" in families):
                paper_id = entry.get("id")
                if isinstance(paper_id, str):
                    ids.append(paper_id)
        return ids[:3]

    def _confidence_from_research(self, research_basis: List[str], research_entries: List[Dict[str, Any]], backtestable: bool) -> float:
        if not research_basis:
            return 0.55 if backtestable else 0.42
        scores = []
        for entry in research_entries:
            if entry.get("id") in research_basis:
                scores.append(QUALITY_SCORE.get(entry.get("research_quality", "medium"), 0.65))
        if not scores:
            return 0.55 if backtestable else 0.42
        score = sum(scores) / len(scores)
        if not backtestable:
            score -= 0.15
        return self._clamp_confidence(score)

    def _generate_supported_code(self, strategy_name: str, strategy_params: Dict[str, Any]) -> str:
        if strategy_name == "trend_follower":
            return (
                "import numpy as np\nimport pandas as pd\n\n"
                "def add_indicators(df: pd.DataFrame) -> pd.DataFrame:\n"
                "    out = df.copy()\n"
                f"    out['ema_fast'] = out['Close'].ewm(span={strategy_params['ema_fast']}, adjust=False).mean()\n"
                f"    out['ema_slow'] = out['Close'].ewm(span={strategy_params['ema_slow']}, adjust=False).mean()\n"
                f"    out['adx_threshold'] = {float(strategy_params['adx_threshold'])}\n"
                "    return out\n\n"
                "def generate_signals(df: pd.DataFrame) -> pd.DataFrame:\n"
                "    out = df.copy()\n"
                "    out['buy_signal'] = (out['ema_fast'] > out['ema_slow']) & (out['ema_fast'].shift(1) <= out['ema_slow'].shift(1))\n"
                "    out['sell_signal'] = (out['ema_fast'] < out['ema_slow']) & (out['ema_fast'].shift(1) >= out['ema_slow'].shift(1))\n"
                "    return out\n"
            )
        if strategy_name == "macd":
            return (
                "import numpy as np\nimport pandas as pd\n\n"
                "def add_indicators(df: pd.DataFrame) -> pd.DataFrame:\n"
                "    out = df.copy()\n"
                f"    out['ema_fast'] = out['Close'].ewm(span={strategy_params['macd_fast']}, adjust=False).mean()\n"
                f"    out['ema_slow'] = out['Close'].ewm(span={strategy_params['macd_slow']}, adjust=False).mean()\n"
                "    out['macd_line'] = out['ema_fast'] - out['ema_slow']\n"
                f"    out['macd_signal'] = out['macd_line'].ewm(span={strategy_params['macd_signal']}, adjust=False).mean()\n"
                "    return out\n\n"
                "def generate_signals(df: pd.DataFrame) -> pd.DataFrame:\n"
                "    out = df.copy()\n"
                "    out['buy_signal'] = out['macd_line'] > out['macd_signal']\n"
                "    out['sell_signal'] = out['macd_line'] < out['macd_signal']\n"
                "    return out\n"
            )
        if strategy_name == "macd_volume_confirmation":
            return (
                "import numpy as np\nimport pandas as pd\n\n"
                "def add_indicators(df: pd.DataFrame) -> pd.DataFrame:\n"
                "    out = df.copy()\n"
                f"    out['ema_fast'] = out['Close'].ewm(span={strategy_params['macd_fast']}, adjust=False).mean()\n"
                f"    out['ema_slow'] = out['Close'].ewm(span={strategy_params['macd_slow']}, adjust=False).mean()\n"
                "    out['macd_line'] = out['ema_fast'] - out['ema_slow']\n"
                f"    out['macd_signal'] = out['macd_line'].ewm(span={strategy_params['macd_signal']}, adjust=False).mean()\n"
                f"    out['volume_ma'] = out['Volume'].rolling({strategy_params['volume_ma_window']}).mean()\n"
                f"    out['volume_confirmed'] = out['Volume'] >= out['volume_ma'] * {float(strategy_params['volume_confirmation_ratio'])}\n"
                "    return out\n\n"
                "def generate_signals(df: pd.DataFrame) -> pd.DataFrame:\n"
                "    out = df.copy()\n"
                "    out['buy_signal'] = (out['macd_line'] > out['macd_signal']) & out['volume_confirmed']\n"
                "    out['sell_signal'] = out['macd_line'] < out['macd_signal']\n"
                "    return out\n"
            )
        if strategy_name == "rsi_adx_filter":
            return (
                "import numpy as np\nimport pandas as pd\n\n"
                "def add_indicators(df: pd.DataFrame) -> pd.DataFrame:\n"
                "    out = df.copy()\n"
                f"    out['bb_mid'] = out['Close'].rolling({strategy_params['bb_window']}).mean()\n"
                f"    rolling_std = out['Close'].rolling({strategy_params['bb_window']}).std()\n"
                f"    out['bb_upper'] = out['bb_mid'] + {float(strategy_params['bb_std'])} * rolling_std\n"
                f"    out['bb_lower'] = out['bb_mid'] - {float(strategy_params['bb_std'])} * rolling_std\n"
                "    return out\n\n"
                "def generate_signals(df: pd.DataFrame) -> pd.DataFrame:\n"
                "    out = df.copy()\n"
                "    out['buy_signal'] = out['Close'] <= out['bb_lower']\n"
                "    out['sell_signal'] = out['Close'] >= out['bb_mid']\n"
                "    return out\n"
            )
        if strategy_name == "rsi_volume_filter":
            return (
                "import numpy as np\nimport pandas as pd\n\n"
                "def add_indicators(df: pd.DataFrame) -> pd.DataFrame:\n"
                "    out = df.copy()\n"
                f"    out['volume_ma'] = out['Volume'].rolling({strategy_params['volume_ma_window']}).mean()\n"
                f"    out['volume_confirmed'] = out['Volume'] >= out['volume_ma'] * {float(strategy_params['volume_confirmation_ratio'])}\n"
                "    return out\n\n"
                "def generate_signals(df: pd.DataFrame) -> pd.DataFrame:\n"
                "    out = df.copy()\n"
                "    out['buy_signal'] = out['volume_confirmed']\n"
                "    out['sell_signal'] = ~out['volume_confirmed']\n"
                "    return out\n"
            )
        return (
            "import numpy as np\nimport pandas as pd\n\n"
            "def add_indicators(df: pd.DataFrame) -> pd.DataFrame:\n"
            "    out = df.copy()\n"
            f"    out['bb_mid'] = out['Close'].rolling({strategy_params['bb_window']}).mean()\n"
            f"    rolling_std = out['Close'].rolling({strategy_params['bb_window']}).std()\n"
            f"    out['bb_upper'] = out['bb_mid'] + {float(strategy_params['bb_std'])} * rolling_std\n"
            f"    out['bb_lower'] = out['bb_mid'] - {float(strategy_params['bb_std'])} * rolling_std\n"
            "    return out\n\n"
            "def generate_signals(df: pd.DataFrame) -> pd.DataFrame:\n"
            "    out = df.copy()\n"
            "    out['buy_signal'] = out['Close'] <= out['bb_lower']\n"
            "    out['sell_signal'] = out['Close'] >= out['bb_upper']\n"
            "    return out\n"
        )

    def _generate_experimental_code(self, strategy_name: str, strategy_params: Dict[str, Any]) -> str:
        param_lines = "\n".join(f"    # {key} = {value}" for key, value in strategy_params.items())
        return (
            "import numpy as np\nimport pandas as pd\n\n"
            "def add_indicators(df: pd.DataFrame) -> pd.DataFrame:\n"
            "    out = df.copy()\n"
            f"{param_lines}\n"
            "    # Add custom indicators here following the add_indicators pattern.\n"
            "    return out\n\n"
            "def generate_signals(df: pd.DataFrame) -> pd.DataFrame:\n"
            "    out = df.copy()\n"
            "    out['buy_signal'] = False\n"
            "    out['sell_signal'] = False\n"
            "    out['position'] = 0\n"
            "    out['buy_marker'] = np.nan\n"
            "    out['sell_marker'] = np.nan\n"
            "    return out\n\n"
            "def run_strategy(price_df: pd.DataFrame, strategy_params: dict) -> pd.DataFrame:\n"
            "    out = add_indicators(price_df)\n"
            "    out = generate_signals(out)\n"
            "    return out\n"
        )

    def _extract_json_object(self, raw_text: str) -> Any:
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return None
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                return None

    def _normalize_strategy_name(self, strategy_name: Any) -> str:
        if strategy_name is None:
            return ""
        normalized = str(strategy_name).strip().lower()
        return STRATEGY_ALIASES.get(normalized, normalized)

    def _normalize_params(self, strategy_name: str, params: Dict[str, Any], backtestable: bool) -> Dict[str, Any]:
        if not backtestable:
            return params if isinstance(params, dict) else {}
        canonical = DEFAULT_PARAM_SETS[strategy_name].copy()
        aliases = PARAM_ALIASES.get(strategy_name, {})
        if not isinstance(params, dict):
            return canonical
        for key, value in params.items():
            normalized_key = aliases.get(key, key)
            if normalized_key in canonical:
                canonical[normalized_key] = value
        return canonical

    def _volatility_bucket(self, market_context: Dict[str, Any]) -> str:
        if "volatility_bucket" in market_context:
            return str(market_context.get("volatility_bucket", "")).lower()
        realized_vol = market_context.get("realized_vol_30d") or market_context.get("volatility")
        try:
            value = float(realized_vol)
        except (TypeError, ValueError):
            return ""
        if value >= 0.45:
            return "high"
        if value <= 0.2:
            return "low"
        return "medium"

    def _clamp_confidence(self, value: Any) -> float:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            confidence = 0.5
        return max(0.0, min(1.0, confidence))

    def _coerce_string_list(self, value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(item) for item in value if item is not None]
        return []

    def _dedupe_specs(self, specs: List[StrategySpec]) -> List[StrategySpec]:
        seen = set()
        deduped: List[StrategySpec] = []
        for spec in specs:
            signature = (spec.strategy_name, spec.backtestable, json.dumps(spec.strategy_params, sort_keys=True, default=str))
            if signature in seen:
                continue
            seen.add(signature)
            deduped.append(spec)
        return deduped
