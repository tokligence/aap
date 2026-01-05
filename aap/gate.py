from pathlib import Path
from typing import Dict

from . import config
from .audit import record_event
from .auth import is_allowed_actor, validate_totp
from .state import ProposalState
from .storage import Proposal
from .utils import dump_yaml_or_json, ensure_dir, utc_now, file_lock


def decision_path(proposal_id: str) -> Path:
    return config.DECISIONS_DIR / f"{proposal_id}.yaml"


def decide(proposal: Proposal, decision: str, actor: str, reason: str = "", otp: str = "") -> Dict[str, str]:
    normalized = decision.lower()
    if normalized not in {"accept", "reject"}:
        raise ValueError("Decision must be 'accept' or 'reject'")

    if not is_allowed_actor(actor):
        raise ValueError(f"Actor {actor} is not in allowlist ({config.AUTH_ALLOWLIST_FILE})")

    if not otp:
        raise ValueError("OTP code required for decision (TOTP)")
    if not validate_totp(otp):
        raise ValueError("Invalid OTP code")

    target_state = ProposalState.ACCEPTED if normalized == "accept" else ProposalState.REJECTED
    proposal.update_state(target_state)

    record = {
        "proposal_id": proposal.id,
        "decision": normalized,
        "by": actor,
        "reason": reason,
        "timestamp": utc_now(),
    }

    proposal.decision = record
    decision_file = decision_path(proposal.id)
    ensure_dir(config.DECISIONS_DIR)

    with file_lock(config.LOCK_DIR / f"{proposal.id}.lock"):
        proposal.save()
        dump_yaml_or_json(record, decision_file)

    record_event("decision", proposal.id, actor, {"decision": normalized, "reason": reason})
    return record
