from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from . import config
from .state import ProposalState, parse_state, transition
from .utils import dump_yaml_or_json, ensure_dir, load_yaml_or_json, utc_now
from .db import upsert_proposal


def proposal_path(proposal_id: str) -> Path:
    return config.PROPOSAL_DIR / f"{proposal_id}.yaml"


@dataclass
class Proposal:
    id: str
    agent: str
    goal: str
    scope: List[str]
    constraints: List[str]
    risk_level: str = "medium"
    policy: Dict[str, Any] = field(default_factory=dict)
    evidence: Dict[str, Any] = field(default_factory=dict)
    decision: Dict[str, Any] = field(default_factory=dict)
    commit: Dict[str, Any] = field(default_factory=dict)
    state: ProposalState = ProposalState.DRAFT
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent": self.agent,
            "goal": self.goal,
            "scope": self.scope,
            "constraints": self.constraints,
            "risk_level": self.risk_level,
            "policy": self.policy,
            "evidence": self.evidence,
            "decision": self.decision,
            "commit": self.commit,
            "state": self.state.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Proposal":
        return cls(
            id=data["id"],
            agent=data["agent"],
            goal=data["goal"],
            scope=data.get("scope", []),
            constraints=data.get("constraints", []),
            risk_level=data.get("risk_level", "medium"),
            policy=data.get("policy", {}),
            evidence=data.get("evidence", {}),
            decision=data.get("decision", {}),
            commit=data.get("commit", {}),
            state=parse_state(data.get("state", "draft")),
            created_at=data.get("created_at", utc_now()),
            updated_at=data.get("updated_at", utc_now()),
        )

    def save(self) -> "Proposal":
        ensure_dir(config.PROPOSAL_DIR)
        self.updated_at = utc_now()
        dump_yaml_or_json(self.to_dict(), proposal_path(self.id))
        try:
            upsert_proposal(self.to_dict())
        except Exception:
            # DB is best-effort; YAML remains source of truth for now
            pass
        return self

    def update_state(self, target: ProposalState) -> None:
        self.state = transition(self.state, target)
        self.updated_at = utc_now()


def list_proposals() -> List[Proposal]:
    ensure_dir(config.PROPOSAL_DIR)
    proposals: List[Proposal] = []
    for path in sorted(config.PROPOSAL_DIR.glob("*.yaml")):
        try:
            proposals.append(load_proposal(path.stem))
        except FileNotFoundError:
            continue
    proposals.sort(key=lambda p: p.updated_at, reverse=True)
    return proposals


def load_proposal(proposal_id: str) -> Proposal:
    path = proposal_path(proposal_id)
    if not path.exists():
        raise FileNotFoundError(f"Proposal {proposal_id} not found at {path}")
    data = load_yaml_or_json(path)
    if not data:
        raise FileNotFoundError(f"Proposal {proposal_id} is empty or invalid")
    return Proposal.from_dict(data)
