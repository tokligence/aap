# Agent Authority Protocol (AAP) MVP

This repository hosts a runnable MVP of the Agent Authority Protocol control-plane. It enforces the AAP state machine, policy/evidence checks, human-gated decisions, scoped commits, and a git guard hook.

- Core code: `aap/` (CLI entrypoint `aap`, FastAPI wrapper optional)
- Quickstart: `docs/quickstart.md`
- Roadmap: `docs/roadmap.md`
- Protocol spec: [tokligence/aap-spec](https://github.com/tokligence/aap-spec)
- License: Apache-2.0

## Project Structure

```
.
├── aap/                    # Core implementation
│   ├── adapters/           # External system adapters
│   │   └── git_adapter.py  # Guarded git commit/tag/push
│   ├── decisions/          # Decision log (one file per proposal)
│   ├── evidence/           # Evidence payloads
│   ├── hooks/              # Git hooks
│   │   └── pre-receive     # AAP enforcement hook
│   ├── locks/              # File locks for concurrency
│   ├── policies/           # Policy definitions
│   │   └── default.yaml    # Sample policy
│   ├── proposals/          # Proposal store (YAML)
│   ├── tests/              # Unit tests
│   ├── api.py              # FastAPI wrapper (optional)
│   ├── auth.py             # Authentication (TOTP, allowlist)
│   ├── cli.py              # CLI entrypoint
│   ├── db.py               # SQLite persistence
│   ├── evaluator.py        # Evidence validator
│   ├── gate.py             # Human accept/reject gate
│   ├── policy.py           # Policy loader/evaluator
│   ├── state.py            # State machine + validation
│   └── storage.py          # Proposal persistence
├── docs/                   # Documentation
│   ├── quickstart.md       # Setup guide
│   └── roadmap.md          # Future plans
├── Makefile                # Build/run targets
└── pyproject.toml          # Python packaging
```

## Installation

Install in editable mode:
```bash
pip install -e .         # CLI
pip install -e .[api]    # + FastAPI
pip install -e .[dev]    # + pytest
```
