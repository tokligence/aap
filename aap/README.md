# AAP MVP (Agent Authority Protocol)

This folder contains a runnable demo of the **Agent Authority Protocol (AAP)** described in `../aap-spec`. It implements the minimum control-plane primitives:

```
PROPOSE → EVALUATE → DECIDE → COMMIT
```

with state enforced as:

```
DRAFT → PROPOSED → EVALUATED → ACCEPTED → COMMITTED
                     ↓
                 REJECTED
```

The CLI is intentionally simple so it can be hardened into a real project without rewriting from scratch.

## Layout

- `cli.py` — CLI entrypoint (`python -m aap.cli ...`)
- `state.py` — state machine + validation
- `policy.py` — policy loader/evaluator (YAML/JSON)
- `evaluator.py` — evidence validator
- `gate.py` — human accept/reject gate
- `storage.py` — proposal persistence (YAML files)
- `adapters/git_adapter.py` — guarded git commit/tag/push helper
- `policies/default.yaml` — sample policy
- `evidence/example/results.json` — sample evidence payload
- `proposals/` — proposal store (created via CLI)
- `decisions/` — decision log (one file per proposal)

## Quickstart

From the repo root:

```bash
# 1) Create a proposal
python -m aap.cli propose \
  --agent claude-code \
  --goal "Add idempotent retry to payment webhook" \
  --scope services/payment/ \
  --constraints no_production_push_by_agent

# 2) Evaluate (policy + evidence)
python -m aap.cli evaluate <proposal_id> \
  --evidence aap/evidence/example/results.json

# 3) Human gate
python -m aap.cli decide <proposal_id> --accept --by you@example.com --reason "Low blast radius"
# or: python -m aap.cli decide <proposal_id> --reject ...

# 4) Commit (only allowed after ACCEPTED)
python -m aap.cli commit <proposal_id> --stage-all --push
# by default tags as aap/<proposal_id>; omit push unless you intend to

# Utilities
python -m aap.cli list
python -m aap.cli show <proposal_id>
python -m aap.cli audit --limit 20
```

Notes:

- Install: `pip install -e .` (or `.[api]` / `.[dev]`). If offline, use `python -m venv .venv --system-site-packages && source .venv/bin/activate && PIP_NO_BUILD_ISOLATION=1 pip install --no-build-isolation --no-deps -e .`.
- Evidence defaults to `aap/evidence/<proposal_id>/results.json` if `--evidence` is omitted.
- Evidence must include metadata keys `runner`, `run_id`, and `artifact_sha256` and required test keys or evaluation fails.
- `commit` uses staged changes unless `--stage-all` is provided. It will refuse to run if nothing is staged.
- `commit` enforces that all staged paths are inside `proposal.scope`; empty scope is rejected.
- A small demo proposal (`demo-proposal`) is present from smoke-testing; delete if undesired.
- Decisions require an allowlisted `--by` email (see `aap/auth_allowlist.txt`) and a valid TOTP code (`--otp`, secret from `AAP_TOTP_SECRET`).
- Audit events are written to `aap/audit.log` and to SQLite (`aap/aap.db`) for basic durability.
- Proposals are also mirrored into SQLite for easier querying (YAML remains primary).

## Policy & Evidence

`policies/default.yaml` encodes a minimal policy:

- Reject scopes touching `auth/`, `infra/prod/`, or `secrets/`
- Require constraint `no_production_push_by_agent`
- Require evidence keys: `unit_tests`, `integration_tests`, `lint`
- Enforce a simple perf budget `max_latency_delta_ms: 5` (compared against `p95_latency_delta_ms` in evidence)
- Require evidence metadata: `runner`, `run_id`, `artifact_sha256`

Evidence files are JSON or YAML; see `evidence/example/results.json` for the expected shape.

## API (optional)

There is a small FastAPI wrapper in `aap/api.py`. Install dependencies (or `pip install -e .[api]`):

```bash
export AAP_API_TOKEN=devtoken  # or add to aap/api_tokens.txt
uvicorn aap.api:app --reload
```

All endpoints require `X-API-Token`.

```bash
# Create a proposal (agent)
curl -XPOST http://localhost:8000/proposals \
  -H "X-API-Token: devtoken" \
  -H "Content-Type: application/json" \
  -d '{"agent":"agent1","goal":"demo","scope":["services/payment/"],"constraints":["no_production_push_by_agent"]}'

# Evaluate with inline evidence
curl -XPOST http://localhost:8000/proposals/<id>/evaluate \
  -H "X-API-Token: devtoken" \
  -H "Content-Type: application/json" \
  -d '{"evidence":{"unit_tests":"pass","integration_tests":"pass","lint":"pass","p95_latency_delta_ms":1.0,"runner":"ci","run_id":"123","artifact_sha256":"abc"}}'

# Human decision (TOTP still required)
curl -XPOST http://localhost:8000/proposals/<id>/decide \
  -H "X-API-Token: devtoken" \
  -H "Content-Type: application/json" \
  -d '{"accept":true,"by":"you@example.com","reason":"ok","otp":"123456"}'
```

## Git pre-receive hook (optional)

A pre-receive hook is provided at `aap/hooks/pre-receive` to block branch pushes that do not point at a commit tagged `aap/<proposal>` with state ACCEPTED/COMMITTED, and to block pushes of AAP tags that are not accepted.

Enable it with:

```bash
ln -s ../../aap/hooks/pre-receive .git/hooks/pre-receive
```

## Quickstart and Makefile

- `docs/quickstart.md` contains a short, copy/paste setup guide.
- `Makefile` provides handy targets:
  - `make deps-base` / `make deps-api`
  - `make propose PROPOSAL_ID=... AGENT=... GOAL="..."`
  - `make evaluate PROPOSAL_ID=... EVIDENCE=...`
  - `make decide PROPOSAL_ID=... OTP=... BY=...`
  - `make commit PROPOSAL_ID=...` (stages all)
  - `make audit LIMIT=20`
  - `make api` (requires `AAP_API_TOKEN`)
  - `make hook` to install the pre-receive guard

## Gaps to close for a production-ready AAP

- **Authority binding** — decisions are not cryptographically bound to humans; add signed attestations (e.g., key-backed signatures, OIDC identity).
- **Trust of evidence** — evidence is accepted at face value; integrate verifiable runners (CI attestations, checksums, provenance).
- **Scope enforcement** — we do not diff changes vs. declared `scope`; add diff validation and capability checks to prevent overreach.
- **Concurrency and locking** — file-backed storage can race; add locking or move to an append-only log/DB with audit trail.
- **Policy lifecycle** — policies are mutable files; version them and restrict write access to human governors only.
- **API surface** — CLI only; expose a small HTTP API (FastAPI) so agents can propose/evaluate without shell access.
- **Git isolation** — commit helper assumes a single repo and user-controlled staging; add worktree/sandbox isolation for agents and guard pushes with server-side hooks.
- **Observability** — no metrics/alerts yet; add structured logging and dashboards for decisions, failures, and unauthorized attempts.
