# Contributing to AAP (MVP)

We welcome contributions that keep authority explicit and controls tight.

## Ground rules
- Do not weaken the authority model (human-in-the-loop, no agent-decided commits).
- Keep policies human-owned; agents must not write `aap/policies/`.
- Preserve state machine invariants (`DRAFT → PROPOSED → EVALUATED → ACCEPTED → COMMITTED; REJECTED`).

## Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Tests
```bash
pytest
```
Add tests for any new logic (state transitions, policy/evidence checks, auth).

## Style
- Python 3.9+, standard library first, avoid unnecessary dependencies.
- Prefer clear functions over cleverness; add brief comments only where intent isn’t obvious.
- Keep CLI/API behavior backwards compatible; document flags/fields if you change them.

## Security and auth
- TOTP secrets and API tokens must never be committed.
- Policies and allowlists are human-owned; changes require review.
- Evidence trust rules must not be relaxed without justification.

## Git hygiene
- Use scoped PRs; include rationale and tests.
- If you edit git guard logic (pre-receive hook or commit checks), call that out explicitly.

## Reporting issues
- Security-sensitive? See `SECURITY.md`.
- Bugs/requests: file an issue with repro steps and expected behavior.
