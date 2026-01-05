from pathlib import Path

# Base directory for the demo implementation
BASE_DIR = Path(__file__).resolve().parent

# Storage locations
PROPOSAL_DIR = BASE_DIR / "proposals"
POLICY_DIR = BASE_DIR / "policies"
EVIDENCE_DIR = BASE_DIR / "evidence"
DECISIONS_DIR = BASE_DIR / "decisions"
LOCK_DIR = BASE_DIR / "locks"
DB_FILE = BASE_DIR / "aap.db"

# Default files
DEFAULT_POLICY_FILE = POLICY_DIR / "default.yaml"

# Git settings
DEFAULT_TAG_PREFIX = "aap/"

# Auth / audit
AUTH_ALLOWLIST_FILE = BASE_DIR / "auth_allowlist.txt"
AUDIT_LOG_FILE = BASE_DIR / "audit.log"
TOTP_SECRET_ENV = "AAP_TOTP_SECRET"
API_TOKEN_ENV = "AAP_API_TOKEN"
API_TOKEN_FILE = BASE_DIR / "api_tokens.txt"
