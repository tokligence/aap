from enum import Enum
from typing import Dict, List


class ProposalState(str, Enum):
    DRAFT = "draft"
    PROPOSED = "proposed"
    EVALUATED = "evaluated"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COMMITTED = "committed"


ALLOWED_TRANSITIONS: Dict[ProposalState, List[ProposalState]] = {
    ProposalState.DRAFT: [ProposalState.PROPOSED],
    ProposalState.PROPOSED: [ProposalState.EVALUATED, ProposalState.REJECTED],
    ProposalState.EVALUATED: [ProposalState.ACCEPTED, ProposalState.REJECTED],
    ProposalState.ACCEPTED: [ProposalState.COMMITTED],
    ProposalState.REJECTED: [],
    ProposalState.COMMITTED: [],
}


def can_transition(current: ProposalState, target: ProposalState) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, [])


def transition(current: ProposalState, target: ProposalState) -> ProposalState:
    if not can_transition(current, target):
        raise ValueError(f"Illegal transition: {current.value} -> {target.value}")
    return target


def parse_state(raw: str) -> ProposalState:
    try:
        return ProposalState(raw)
    except ValueError as exc:
        raise ValueError(f"Unknown proposal state: {raw}") from exc
