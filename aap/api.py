"""FastAPI wrapper around the AAP MVP for agents/humans via HTTP."""

from typing import List, Optional
from uuid import uuid4
from pathlib import Path

try:
    from fastapi import Depends, FastAPI, Header, HTTPException
    from pydantic import BaseModel
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "FastAPI not installed. Install with: pip install fastapi uvicorn\n"
        "You can still use the CLI via `python -m aap.cli`."
    ) from exc

from . import config
from .audit import record_event
from .evaluator import evaluate_evidence
from .gate import decide
from .policy import evaluate_policy, load_policy
from .state import ProposalState
from .storage import Proposal, list_proposals, load_proposal, proposal_path
from .utils import file_lock, sha256_file, utc_now


def _load_api_tokens() -> set[str]:
    tokens = set()
    env_token = None
    try:
        env_token = __import__("os").environ.get(config.API_TOKEN_ENV)
    except Exception:
        env_token = None
    if env_token:
        tokens.add(env_token.strip())
    path = config.API_TOKEN_FILE
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                tokens.add(line)
    return tokens


def require_token(x_api_token: Optional[str] = Header(None)) -> str:
    tokens = _load_api_tokens()
    if not tokens:
        raise HTTPException(status_code=500, detail="API token not configured")
    if not x_api_token or x_api_token not in tokens:
        raise HTTPException(status_code=401, detail="Invalid or missing API token")
    return x_api_token


class ProposalIn(BaseModel):
    agent: str
    goal: str
    scope: List[str] = []
    constraints: List[str] = []
    risk_level: str = "medium"
    id: Optional[str] = None
    policy: Optional[str] = None


class EvidenceIn(BaseModel):
    evidence: dict
    policy: Optional[str] = None


class DecisionIn(BaseModel):
    accept: bool
    by: str
    reason: Optional[str] = None
    otp: str


app = FastAPI(title="AAP MVP API", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/proposals")
def get_proposals(_: str = Depends(require_token)):
    return [p.to_dict() for p in list_proposals()]


@app.get("/proposals/{proposal_id}")
def get_proposal(proposal_id: str, _: str = Depends(require_token)):
    try:
        proposal = load_proposal(proposal_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return proposal.to_dict()


@app.post("/proposals")
def create_proposal(body: ProposalIn, token: str = Depends(require_token)):
    proposal_id = body.id or uuid4().hex[:8]
    path = proposal_path(proposal_id)
    if path.exists():
        raise HTTPException(status_code=400, detail="Proposal id already exists")

    proposal = Proposal(
        id=proposal_id,
        agent=body.agent,
        goal=body.goal,
        scope=body.scope,
        constraints=body.constraints,
        risk_level=body.risk_level,
        policy={
            "name": body.policy or "default",
            "path": body.policy or str(config.DEFAULT_POLICY_FILE),
        },
    )
    proposal.update_state(ProposalState.PROPOSED)
    with file_lock(config.LOCK_DIR / f"{proposal_id}.lock"):
        proposal.save()

    record_event(
        "propose",
        proposal_id,
        body.agent,
        {"goal": proposal.goal, "scope": proposal.scope, "constraints": proposal.constraints},
    )
    return proposal.to_dict()


@app.post("/proposals/{proposal_id}/evaluate")
def evaluate_proposal(proposal_id: str, body: EvidenceIn, token: str = Depends(require_token)):
    try:
        proposal = load_proposal(proposal_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if proposal.state in {ProposalState.REJECTED, ProposalState.COMMITTED}:
        raise HTTPException(status_code=400, detail="Cannot evaluate in this state")

    policy_path = body.policy or str(config.DEFAULT_POLICY_FILE)
    policy = load_policy(Path(policy_path))
    policy_hash = sha256_file(Path(policy_path))
    policy_eval = evaluate_policy(proposal, policy)

    proposal.policy = {
        "name": policy_eval.policy_name,
        "path": str(policy_path),
        "hash": policy_hash,
        "passed": policy_eval.passed,
        "violations": policy_eval.violations,
        "required_evidence": policy_eval.required_evidence,
        "performance_budget_ms": policy_eval.performance_budget_ms,
        "evaluated_at": utc_now(),
    }

    evidence_eval = evaluate_evidence(
        body.evidence,
        policy_eval.required_evidence,
        required_metadata=["runner", "run_id", "artifact_sha256"],
        performance_budget_ms=policy_eval.performance_budget_ms,
    )
    proposal.evidence = {
        "path": "inline",
        "passed": evidence_eval.passed,
        "missing": evidence_eval.missing,
        "failures": evidence_eval.failures,
        "metadata_missing": evidence_eval.metadata_missing,
        "metadata_invalid": evidence_eval.metadata_invalid,
        "performance": evidence_eval.performance,
        "performance_budget_ms": evidence_eval.performance_budget_ms,
        "evaluated_at": utc_now(),
    }

    if policy_eval.passed and evidence_eval.passed and proposal.state == ProposalState.PROPOSED:
        proposal.update_state(ProposalState.EVALUATED)

    with file_lock(config.LOCK_DIR / f"{proposal.id}.lock"):
        proposal.save()

    record_event(
        "evaluate",
        proposal.id,
        proposal.agent,
        {
            "policy_passed": policy_eval.passed,
            "policy_violations": policy_eval.violations,
            "evidence_passed": evidence_eval.passed,
        },
    )
    return proposal.to_dict()


@app.post("/proposals/{proposal_id}/decide")
def decide_proposal(proposal_id: str, body: DecisionIn, token: str = Depends(require_token)):
    try:
        proposal = load_proposal(proposal_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Proposal not found")
    decision = "accept" if body.accept else "reject"
    try:
        record = decide(
            proposal,
            decision=decision,
            actor=body.by,
            reason=body.reason or "",
            otp=body.otp,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"decision": record}
