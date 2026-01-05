# AAP MVP → Usable Project Roadmap

This roadmap tracks how we harden the AAP MVP into a practical control-plane. Each area lists short-term steps for immediate usability, plus medium/long-term options.

## Authority Binding (decisions & commits)
- Short term: Require `--by` to be an allowlisted email; store hashed email + TOTP code per decision; refuse DECIDE without both.
- Medium: OIDC for humans (CLI/API) issuing signed JWT stored with decisions; include JWK thumbprint.
- Long: Hardware-backed signatures (WebAuthn/FIDO2) for DECIDE; sign commit attestation files and verify before COMMIT/PUSH.

## Evidence Provenance
- Short term: Evidence must include runner metadata + checksum (e.g., `runner`, `run_id`, `artifact_sha256`); reject if missing.
- Medium: Accept evidence only from controlled CI; validate a signed attestation (in-toto/SLSA provenance) before PASS.
- Long: Bind CI OIDC identity to repo/workflow/run_id; store provenance in append-only log (e.g., immutability store).

## Scope Enforcement (prevent overreach)
- Short term: On COMMIT, diff staged changes and ensure all paths are within `proposal.scope`; fail otherwise.
- Medium: Capability labels per agent; block PROPOSE/EVALUATE if scope not covered; enforce same at COMMIT.
- Long: Hash a manifest of touched components and require it to match an ACCEPTED proposal (checked in server-side hook).

## Storage, Audit, Locking
- Short term: Move proposal/decision metadata to SQLite (WAL); record every state transition with actor+timestamp; add file locks for evidence writes.
- Medium: Append-only event log with materialized views; audit endpoint for transitions.
- Long: Tamper-evident log (Merkle/immudb) with periodic checkpoints to object storage.

## Policy Lifecycle & Governance
- Short term: Version policies and store policy hash in proposal; only humans can modify `policies/`.
- Medium: Policy registry with signed releases; proposals reference a specific version; block evaluate if unapproved.
- Long: Policy changes follow their own proposal/decision workflow (agents cannot alter policies).

## API Surface & AuthZ
- Short term: Wrap CLI handlers with FastAPI; API tokens per agent/human; log IP/user-agent.
- Medium: OIDC for humans; scoped tokens for agents (`propose/evaluate` only); rate-limit agent endpoints.
- Long: mTLS for agents plus signed PROPOSE payloads.

## Git Isolation & Push Control
- Short term: Per-proposal worktrees; forbid direct agent pushes; commit helper runs in the worktree.
- Medium: Server-side pre-receive hook requiring ACCEPTED proposal id + tag `aap/<id>`; block otherwise.
- Long: Dedicated agent mirror repo; human push via ACP automation with short-lived deploy keys.

## Observability & Alerts
- Short term: Structured JSON logs for propose/evaluate/decide/commit; basic counters by state/failure.
- Medium: Prometheus metrics + alerts (e.g., repeated REJECTs, push attempts without ACCEPT).
- Long: SIEM integration (ELK/Splunk) with correlation rules for suspicious agent activity.

## Concurrency & Race Handling
- Short term: Per-proposal locks during evaluate/decide/commit; reject stale transitions.
- Medium: Optimistic concurrency with version numbers; retry-safe operations.
- Long: Event-sourced state machine with idempotent handlers.

## UX/Ops Hardening
- Short term: `--dry-run` on commit; `--explain` for failures; quotas per agent on PROPOSED/EVALUATED.
- Medium: Backups of proposals/evidence to object storage; tested restore path.
- Long: Admin dashboards for policy/version/agent health.
