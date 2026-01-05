# Security Policy

## Reporting a vulnerability
- Please do not open a public issue for security reports.
- Email the maintainers (see repository owner/contact) with:
  - A clear description of the issue
  - Reproduction steps or proof-of-concept
  - Impact assessment if known
- If no response within 5 business days, follow up or request a private channel for details.

## Scope
- Control-plane logic (state machine, decisions, commits)
- Authn/z around decisions (TOTP, allowlist, tokens)
- Git guard (pre-receive hook) and evidence/policy validation

## Out of scope
- Model correctness or agent code generation quality
- Issues in downstream repos or third-party services
