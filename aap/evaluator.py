from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import config
from .utils import load_yaml_or_json


def evidence_path(proposal_id: str, filename: str = "results.json") -> Path:
    return config.EVIDENCE_DIR / proposal_id / filename


@dataclass
class EvidenceEvaluation:
    passed: bool
    missing: List[str]
    failures: List[str]
    performance: Optional[float]
    performance_budget_ms: Optional[float]
    metadata_missing: List[str]
    metadata_invalid: List[str]


def load_evidence(path: Path) -> Dict[str, Any]:
    data = load_yaml_or_json(path)
    if not data:
        raise FileNotFoundError(f"Evidence missing or empty at {path}")
    return data


def evaluate_evidence(
    evidence: Dict[str, Any],
    required_keys: List[str],
    required_metadata: Optional[List[str]] = None,
    performance_budget_ms: Optional[float] = None,
) -> EvidenceEvaluation:
    missing = [key for key in required_keys if key not in evidence]
    failures: List[str] = []
    metadata_missing: List[str] = []
    metadata_invalid: List[str] = []

    for key in required_keys:
        if key in missing:
            continue
        value = evidence.get(key)
        if isinstance(value, str):
            normalized = value.lower()
            if normalized not in {"pass", "passed", "ok", "success"}:
                failures.append(f"{key}={value}")
        else:
            if value not in {True, "pass"}:
                failures.append(f"{key}={value}")

    if required_metadata:
        for meta in required_metadata:
            if meta not in evidence:
                metadata_missing.append(meta)
                continue
            val = evidence.get(meta)
            if val in (None, "", []):
                metadata_invalid.append(f"{meta}=<empty>")

    perf_value = evidence.get("p95_latency_delta_ms")
    perf_numeric: Optional[float] = None
    perf_budget_exceeded = False
    perf_budget = None
    if performance_budget_ms is not None and perf_value is not None:
        try:
            perf_numeric = float(perf_value)
            perf_budget = float(performance_budget_ms)
            if perf_numeric > perf_budget:
                perf_budget_exceeded = True
                failures.append(
                    f"p95_latency_delta_ms={perf_numeric} exceeds budget {perf_budget}"
                )
        except (TypeError, ValueError):
            failures.append(f"Invalid performance value: {perf_value}")
    else:
        try:
            perf_numeric = float(perf_value) if perf_value is not None else None
        except (TypeError, ValueError):
            perf_numeric = None

    passed = (
        len(missing) == 0
        and len(failures) == 0
        and len(metadata_missing) == 0
        and len(metadata_invalid) == 0
        and not perf_budget_exceeded
    )

    return EvidenceEvaluation(
        passed=passed,
        missing=missing,
        failures=failures,
        performance=perf_numeric,
        performance_budget_ms=perf_budget,
        metadata_missing=metadata_missing,
        metadata_invalid=metadata_invalid,
    )
