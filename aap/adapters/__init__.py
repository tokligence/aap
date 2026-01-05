"""Adapters for integrating AAP with external systems (e.g., git)."""

from .git_adapter import (  # noqa: F401
    create_commit,
    create_tag,
    default_repo_root,
    ensure_repo,
    has_staged_changes,
    list_staged_files,
    push,
    stage_all,
)
