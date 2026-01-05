import json
from datetime import datetime, timezone
import hashlib
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None


def utc_now() -> str:
    """Return an ISO 8601 timestamp with Z suffix."""
    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_yaml_or_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text()
    if not text.strip():
        return {}
    if yaml:
        return yaml.safe_load(text) or {}
    return json.loads(text)


def dump_yaml_or_json(data: Dict[str, Any], path: Path) -> None:
    ensure_dir(path.parent)
    if yaml:
        serialized = yaml.safe_dump(data, sort_keys=False)
        path.write_text(serialized)
    else:
        path.write_text(json.dumps(data, indent=2))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def read_allowlist(path: Path) -> Set[str]:
    if not path.exists():
        return set()
    entries: List[str] = []
    with path.open() as f:
        for line in f:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                entries.append(stripped.lower())
    return set(entries)


@contextmanager
def file_lock(lock_path: Path):
    """Advisory lock using fcntl (best-effort)."""
    ensure_dir(lock_path.parent)
    import fcntl

    with lock_path.open("w") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
