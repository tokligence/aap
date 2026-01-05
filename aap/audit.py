import json
from pathlib import Path
from typing import Any, Dict

from . import config
from .db import insert_event
from .utils import ensure_dir, utc_now, file_lock


def record_event(event_type: str, proposal_id: str, actor: str, data: Dict[str, Any]) -> None:
    ensure_dir(config.AUDIT_LOG_FILE.parent)
    entry = {
        "timestamp": utc_now(),
        "event": event_type,
        "proposal_id": proposal_id,
        "actor": actor,
        "data": data,
    }
    lock_path = config.LOCK_DIR / "audit.log.lock"
    with file_lock(lock_path):
        with config.AUDIT_LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False))
            f.write("\n")
    # Best-effort SQLite write; failures should not block
    try:
        insert_event(entry["timestamp"], event_type, proposal_id, actor, data)
    except Exception:
        pass
