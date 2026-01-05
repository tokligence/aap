from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import config
from .storage import Proposal
from .utils import load_yaml_or_json


@dataclass
class PolicyEvaluation:
    passed: bool
    violations: List[str]
    required_evidence: List[str]
    policy_name: str
    performance_budget_ms: Optional[float]


def load_policy(path: Optional[Path] = None) -> Dict[str, Any]:
    policy_path = path or config.DEFAULT_POLICY_FILE
    data = load_yaml_or_json(policy_path)
    if not data:
        raise ValueError(f"Policy file is empty or missing: {policy_path}")
    return data


def evaluate_policy(proposal: Proposal, policy: Dict[str, Any]) -> PolicyEvaluation:
    violations: List[str] = []
    rules: Dict[str, Any] = policy.get("rules", {})
    policy_name = policy.get("name", "default")

    allowed_risks = policy.get("applies_to")
    if allowed_risks:
        allowed = allowed_risks if isinstance(allowed_risks, list) else [allowed_risks]
        if proposal.risk_level not in allowed:
            violations.append(f"risk_level {proposal.risk_level} not allowed (policy allows {allowed})")

    forbid_paths = rules.get("forbid_paths", [])
    for pattern in forbid_paths:
        for path in proposal.scope:
            if pattern in path:
                violations.append(f"path '{path}' violates forbid_paths rule '{pattern}'")

    required_constraints = rules.get("require_constraints", [])
    for constraint in required_constraints:
        if constraint not in proposal.constraints:
            violations.append(f"missing required constraint '{constraint}'")

    required_evidence = rules.get("require_evidence", ["unit_tests", "integration_tests"])
    performance_budget_ms = rules.get("max_latency_delta_ms")

    return PolicyEvaluation(
        passed=len(violations) == 0,
        violations=violations,
        required_evidence=required_evidence,
        policy_name=policy_name,
        performance_budget_ms=performance_budget_ms,
    )
