# AAP Quickstart (MVP)

Follow these steps to get the AAP demo running with the short-term controls enabled.

## Prerequisites
- Python 3.9+
- Install the package (editable for local dev):
  ```bash
  # Standard
  pip install -e .
  # API extras
  pip install -e .[api]
  # Dev extras (api + pytest)
  pip install -e .[dev]
  ```
- Offline-friendly tip: if your environment cannot reach PyPI, create a venv with system site packages and skip deps download:
  ```bash
  python -m venv .venv --system-site-packages
  source .venv/bin/activate
  PIP_NO_BUILD_ISOLATION=1 pip install --no-build-isolation --no-deps -e .
  ```
- A Git repo if you want commit/tag/push enforcement

## One-time setup
1) Set a TOTP secret for human decisions (base32 works):
   ```bash
   export AAP_TOTP_SECRET=JBSWY3DPEHPK3PXP
   ```
2) Add yourself to the allowlist: `echo "you@example.com" >> aap/auth_allowlist.txt`
3) (Optional) API token: `export AAP_API_TOKEN=devtoken` or add to `aap/api_tokens.txt`
4) (Optional) Enable git guard: `ln -s ../../aap/hooks/pre-receive .git/hooks/pre-receive`

## CLI flow
```bash
# Create a proposal
python -m aap.cli propose \
  --agent claude \
  --goal "Add retry to webhook" \
  --scope services/payment/ \
  --constraints no_production_push_by_agent

# Evaluate (requires evidence + metadata)
python -m aap.cli evaluate <proposal_id> \
  --evidence aap/evidence/example/results.json

# Get a TOTP code for the decision
OTP=$(python - <<'PY'\nfrom aap.auth import totp_now; print(totp_now())\nPY)

# Human decision (allowlist + TOTP enforced)
python -m aap.cli decide <proposal_id> --accept \
  --by you@example.com --reason "ok" --otp "$OTP"

# Commit (must be ACCEPTED; staged files must be within proposal.scope)
python -m aap.cli commit <proposal_id> --stage-all  # add --push if desired

# Inspect
python -m aap.cli list
python -m aap.cli show <proposal_id>
python -m aap.cli audit --limit 20
```

## FastAPI (optional)
```bash
pip install fastapi uvicorn
export AAP_API_TOKEN=devtoken  # or set in aap/api_tokens.txt
uvicorn aap.api:app --reload
```
All endpoints require `X-API-Token`. TOTP + allowlist still gate `/decide`.

## Evidence format reminder
Evidence must include:
- `unit_tests`, `integration_tests`, `lint`
- `runner`, `run_id`, `artifact_sha256`
- Optional perf check: `p95_latency_delta_ms`

See `aap/evidence/example/results.json` for a template.
