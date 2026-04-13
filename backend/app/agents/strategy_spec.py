from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class StrategySpec:
    strategy_name: str
    strategy_params: Dict[str, Any]
    description: str
    rationale: str = ""
    source: str = "rule_based"
    backtestable: bool = True
    confidence: float = 0.5
    research_basis: List[str] = field(default_factory=list)
    generated_code: Optional[str] = None
    implementation_hint: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
