import argparse
from pathlib import Path
from typing import Optional
from uuid import uuid4

from . import config
from .adapters import git_adapter
from .audit import record_event
from .evaluator import evaluate_evidence, evidence_path, load_evidence
from .gate import decide
from .policy import evaluate_policy, load_policy
from .state import ProposalState
from .storage import Proposal, list_proposals, load_proposal, proposal_path
from .utils import utc_now, sha256_file, file_lock


def generate_id() -> str:
    return uuid4().hex[:8]


def handle_propose(args: argparse.Namespace) -> None:
    proposal_id = args.id or generate_id()
    path = proposal_path(proposal_id)
    if path.exists():
        raise SystemExit(f"Proposal {proposal_id} already exists at {path}")

    proposal = Proposal(
        id=proposal_id,
        agent=args.agent,
        goal=args.goal,
        scope=args.scope or [],
        constraints=args.constraints or [],
        risk_level=args.risk_level,
        policy={
            "name": Path(args.policy).stem if args.policy else "default",
            "path": str(Path(args.policy)) if args.policy else str(config.DEFAULT_POLICY_FILE),
        },
    )
    proposal.update_state(ProposalState.PROPOSED)
    with file_lock(config.LOCK_DIR / f"{proposal_id}.lock"):
        proposal.save()

    record_event(
        "propose",
        proposal_id,
        args.agent,
        {"goal": proposal.goal, "scope": proposal.scope, "constraints": proposal.constraints},
    )

    print(f"Created proposal {proposal_id}")
    print(f"  agent: {proposal.agent}")
    print(f"  goal:  {proposal.goal}")
    print(f"  scope: {', '.join(proposal.scope) or '(none)'}")
    print(f"  constraints: {', '.join(proposal.constraints) or '(none)'}")
    print(f"  policy: {proposal.policy.get('name')}")


def handle_evaluate(args: argparse.Namespace) -> None:
    proposal = load_proposal(args.proposal_id)
    if proposal.state in {ProposalState.REJECTED, ProposalState.COMMITTED}:
        raise SystemExit(f"Proposal {proposal.id} is {proposal.state.value}; cannot evaluate.")

    policy_path = Path(args.policy) if args.policy else config.DEFAULT_POLICY_FILE
    policy = load_policy(policy_path)
    policy_hash = sha256_file(policy_path)
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

    evidence_file = Path(args.evidence) if args.evidence else evidence_path(proposal.id)
    evidence_eval = None
    try:
        evidence_data = load_evidence(evidence_file)
        evidence_eval = evaluate_evidence(
            evidence_data,
            policy_eval.required_evidence,
            required_metadata=["runner", "run_id", "artifact_sha256"],
            performance_budget_ms=policy_eval.performance_budget_ms,
        )
        proposal.evidence = {
            "path": str(evidence_file),
            "passed": evidence_eval.passed,
            "missing": evidence_eval.missing,
            "failures": evidence_eval.failures,
            "metadata_missing": evidence_eval.metadata_missing,
            "metadata_invalid": evidence_eval.metadata_invalid,
            "performance": evidence_eval.performance,
            "performance_budget_ms": evidence_eval.performance_budget_ms,
            "evaluated_at": utc_now(),
        }
    except FileNotFoundError as exc:
        proposal.evidence = {
            "path": str(evidence_file),
            "passed": False,
            "missing": policy_eval.required_evidence,
            "failures": [str(exc)],
            "evaluated_at": utc_now(),
        }

    should_advance = policy_eval.passed and evidence_eval and evidence_eval.passed
    if should_advance and proposal.state == ProposalState.PROPOSED:
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
            "evidence_passed": bool(evidence_eval and evidence_eval.passed),
        },
    )

    print(f"Policy:   {'PASS' if policy_eval.passed else 'FAIL'}")
    if policy_eval.violations:
        for v in policy_eval.violations:
            print(f"  - {v}")
    print(f"Evidence: {'PASS' if evidence_eval and evidence_eval.passed else 'FAIL'}")
    if proposal.evidence.get("failures"):
        for f in proposal.evidence["failures"]:
            print(f"  - {f}")
    if proposal.evidence.get("missing"):
        for m in proposal.evidence["missing"]:
            print(f"  - missing {m}")
    if proposal.evidence.get("metadata_missing"):
        for m in proposal.evidence["metadata_missing"]:
            print(f"  - missing metadata {m}")
    if proposal.evidence.get("metadata_invalid"):
        for m in proposal.evidence["metadata_invalid"]:
            print(f"  - invalid metadata {m}")
    print(f"State:    {proposal.state.value.upper()}")


def handle_decide(args: argparse.Namespace) -> None:
    proposal = load_proposal(args.proposal_id)
    decision = "accept" if args.accept else "reject"
    actor = args.by or "human"
    try:
        record = decide(
            proposal,
            decision=decision,
            actor=actor,
            reason=args.reason or "",
            otp=args.otp or "",
        )
    except ValueError as exc:
        raise SystemExit(str(exc))
    print(f"{decision.upper()} proposal {proposal.id} by {actor}")
    if record.get("reason"):
        print(f"Reason: {record['reason']}")
    print(f"State:  {proposal.state.value}")


def handle_commit(args: argparse.Namespace) -> None:
    proposal = load_proposal(args.proposal_id)
    if proposal.state != ProposalState.ACCEPTED:
        raise SystemExit(f"Proposal {proposal.id} must be ACCEPTED before commit (current: {proposal.state.value}).")

    repo_root = git_adapter.default_repo_root()
    if args.stage_all:
        git_adapter.stage_all(cwd=repo_root)

    # Scope enforcement: ensure staged changes are within declared scope
    staged = git_adapter.list_staged_files(cwd=repo_root)
    if not staged:
        raise SystemExit("No staged changes. Stage files or pass --stage-all.")
    if not proposal.scope:
        raise SystemExit("Proposal scope is empty; cannot commit.")
    violations = []
    for path in staged:
        if not any(path.startswith(scope) for scope in proposal.scope):
            violations.append(path)
    if violations:
        raise SystemExit(f"Staged paths outside scope: {', '.join(violations)}")

    message = args.message or f"aap:{proposal.id} {proposal.goal}"
    try:
        commit_sha = git_adapter.create_commit(
            message=message, cwd=repo_root, stage_all_changes=args.stage_all
        )
        tag_name: Optional[str] = None
        if args.tag:
            tag_name = f"{config.DEFAULT_TAG_PREFIX}{proposal.id}"
            git_adapter.create_tag(tag_name, message=f"AAP {proposal.id}", cwd=repo_root)
        if args.push:
            git_adapter.push(branch=args.branch, push_tags=args.tag, cwd=repo_root)
    except RuntimeError as exc:
        raise SystemExit(str(exc))

    proposal.update_state(ProposalState.COMMITTED)
    proposal.commit = {
        "message": message,
        "sha": commit_sha,
        "tag": tag_name,
        "pushed": args.push,
        "branch": args.branch,
        "committed_at": utc_now(),
    }
    with file_lock(config.LOCK_DIR / f"{proposal.id}.lock"):
        proposal.save()

    record_event(
        "commit",
        proposal.id,
        actor="system",
        data={"sha": commit_sha, "tag": tag_name, "pushed": args.push, "branch": args.branch},
    )

    print(f"Committed proposal {proposal.id} -> {commit_sha}")
    if tag_name:
        print(f"Tagged: {tag_name}")
    if args.push:
        print("Pushed to remote.")
    else:
        print("Push skipped (use --push to push).")


def handle_list(_: argparse.Namespace) -> None:
    proposals = list_proposals()
    if not proposals:
        print("No proposals recorded.")
        return
    for p in proposals:
        print(f"{p.id} [{p.state.value}] agent={p.agent} goal={p.goal}")


def handle_audit(args: argparse.Namespace) -> None:
    try:
        from .db import list_events
    except Exception as exc:
        raise SystemExit(f"Cannot read audit log: {exc}")
    events = list_events(limit=args.limit)
    if not events:
        print("No audit events.")
        return
    for ev in events:
        print(f"{ev['timestamp']} {ev['event']} proposal={ev['proposal_id']} actor={ev['actor']} data={ev['data']}")


def handle_show(args: argparse.Namespace) -> None:
    proposal = load_proposal(args.proposal_id)
    print(f"id: {proposal.id}")
    print(f"agent: {proposal.agent}")
    print(f"goal: {proposal.goal}")
    print(f"scope: {', '.join(proposal.scope)}")
    print(f"constraints: {', '.join(proposal.constraints)}")
    print(f"risk_level: {proposal.risk_level}")
    print(f"state: {proposal.state.value}")
    if proposal.policy:
        print(f"policy: {proposal.policy}")
    if proposal.evidence:
        print(f"evidence: {proposal.evidence}")
    if proposal.decision:
        print(f"decision: {proposal.decision}")
    if proposal.commit:
        print(f"commit: {proposal.commit}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AAP MVP control-plane CLI")
    sub = parser.add_subparsers(dest="command")

    propose = sub.add_parser("propose", help="Create a new proposal")
    propose.add_argument("--agent", required=True, help="Agent identifier")
    propose.add_argument("--goal", required=True, help="Intent/goal for the proposal")
    propose.add_argument(
        "--scope",
        nargs="*",
        default=[],
        help="Paths or components affected by the proposal",
    )
    propose.add_argument(
        "--constraints",
        nargs="*",
        default=[],
        help="Constraint identifiers applied to this proposal",
    )
    propose.add_argument("--risk-level", default="medium", help="Risk level label")
    propose.add_argument("--policy", help="Path to policy file (YAML/JSON)")
    propose.add_argument("--id", help="Optional proposal id")
    propose.set_defaults(func=handle_propose)

    evaluate = sub.add_parser("evaluate", help="Evaluate a proposal against policy + evidence")
    evaluate.add_argument("proposal_id")
    evaluate.add_argument("--policy", help="Path to policy file")
    evaluate.add_argument("--evidence", help="Path to evidence file (JSON/YAML)")
    evaluate.set_defaults(func=handle_evaluate)

    decide_cmd = sub.add_parser("decide", help="Record a human accept/reject decision")
    decide_cmd.add_argument("proposal_id")
    group = decide_cmd.add_mutually_exclusive_group(required=True)
    group.add_argument("--accept", action="store_true", help="Accept the proposal")
    group.add_argument("--reject", action="store_true", help="Reject the proposal")
    decide_cmd.add_argument("--by", help="Decision maker identifier")
    decide_cmd.add_argument("--reason", help="Reason for the decision")
    decide_cmd.add_argument("--otp", help="TOTP code for the decision")
    decide_cmd.set_defaults(func=handle_decide)

    commit_cmd = sub.add_parser("commit", help="Commit an accepted proposal to git")
    commit_cmd.add_argument("proposal_id")
    commit_cmd.add_argument("--message", help="Commit message override")
    commit_cmd.add_argument("--stage-all", action="store_true", help="Stage all changes before commit")
    commit_cmd.add_argument("--tag", action="store_true", default=True, help="Create a tag aap/<id>")
    commit_cmd.add_argument("--no-tag", dest="tag", action="store_false")
    commit_cmd.add_argument("--push", action="store_true", help="Push commit (and tag if created)")
    commit_cmd.add_argument("--branch", help="Branch to push (default: current)")
    commit_cmd.set_defaults(func=handle_commit)

    list_cmd = sub.add_parser("list", help="List proposals")
    list_cmd.set_defaults(func=handle_list)

    audit_cmd = sub.add_parser("audit", help="Show recent audit events")
    audit_cmd.add_argument("--limit", type=int, default=50, help="Number of events to show")
    audit_cmd.set_defaults(func=handle_audit)

    show_cmd = sub.add_parser("show", help="Show proposal details")
    show_cmd.add_argument("proposal_id")
    show_cmd.set_defaults(func=handle_show)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
