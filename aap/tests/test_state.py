import pytest

from aap.state import ProposalState, transition
from aap.evaluator import evaluate_evidence


def test_valid_transition():
    assert transition(ProposalState.PROPOSED, ProposalState.EVALUATED) == ProposalState.EVALUATED
    assert transition(ProposalState.EVALUATED, ProposalState.ACCEPTED) == ProposalState.ACCEPTED


def test_invalid_transition_raises():
    with pytest.raises(ValueError):
        transition(ProposalState.DRAFT, ProposalState.ACCEPTED)
    with pytest.raises(ValueError):
        transition(ProposalState.COMMITTED, ProposalState.PROPOSED)


def test_evidence_metadata_required():
    evidence = {
        "unit_tests": "pass",
        "integration_tests": "pass",
        "lint": "pass",
    }
    result = evaluate_evidence(
        evidence,
        required_keys=["unit_tests", "integration_tests", "lint"],
        required_metadata=["runner", "artifact_sha256"],
    )
    assert not result.passed
    assert "runner" in result.metadata_missing
    assert "artifact_sha256" in result.metadata_missing


def test_evidence_perf_budget():
    evidence = {
        "unit_tests": "pass",
        "integration_tests": "pass",
        "lint": "pass",
        "runner": "ci",
        "artifact_sha256": "abc",
        "p95_latency_delta_ms": 10,
    }
    result = evaluate_evidence(
        evidence,
        required_keys=["unit_tests", "integration_tests", "lint"],
        required_metadata=["runner", "artifact_sha256"],
        performance_budget_ms=5,
    )
    assert not result.passed
    assert any("p95_latency_delta_ms" in f for f in result.failures)
