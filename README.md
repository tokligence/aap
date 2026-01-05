# Agent Authority Protocol (AAP) MVP

This repository hosts a runnable MVP of the Agent Authority Protocol control-plane. It enforces the AAP state machine, policy/evidence checks, human-gated decisions, scoped commits, and a git guard hook.

- Core code: `aap/` (CLI entrypoint `aap`, FastAPI wrapper optional)
- Quickstart: `docs/quickstart.md`
- Roadmap: `docs/roadmap.md`
- License: Apache-2.0

Install in editable mode:
```bash
pip install -e .         # CLI
pip install -e .[api]    # + FastAPI
pip install -e .[dev]    # + pytest
```
