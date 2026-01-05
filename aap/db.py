import json
import sqlite3
from pathlib import Path
from typing import Any, Dict

from . import config
from .utils import ensure_dir, file_lock


def _connect() -> sqlite3.Connection:
    ensure_dir(config.DB_FILE.parent)
    conn = sqlite3.connect(config.DB_FILE)
    conn.execute("pragma journal_mode=WAL;")
    conn.execute("pragma foreign_keys=ON;")
    return conn


def init_db() -> None:
    with file_lock(config.LOCK_DIR / "db.lock"):
        conn = _connect()
        try:
            conn.execute(
                """
                create table if not exists events (
                    id integer primary key autoincrement,
                    ts text not null,
                    event text not null,
                    proposal_id text,
                    actor text,
                    data text
                );
                """
            )
            conn.execute(
                """
                create table if not exists proposals (
                    id text primary key,
                    agent text,
                    goal text,
                    scope text,
                    constraints text,
                    risk_level text,
                    state text,
                    policy text,
                    evidence text,
                    decision text,
                    commit_data text,
                    created_at text,
                    updated_at text
                );
                """
            )
            conn.commit()
        finally:
            conn.close()


def insert_event(ts: str, event: str, proposal_id: str, actor: str, data: Dict[str, Any]) -> None:
    init_db()
    with file_lock(config.LOCK_DIR / "db.lock"):
        conn = _connect()
        try:
            conn.execute(
                "insert into events (ts, event, proposal_id, actor, data) values (?, ?, ?, ?, ?)",
                (ts, event, proposal_id, actor, json.dumps(data, ensure_ascii=False)),
            )
            conn.commit()
        finally:
            conn.close()


def upsert_proposal(data: Dict[str, Any]) -> None:
    """Persist proposal snapshot (YAML remains source-of-truth for now)."""
    init_db()
    with file_lock(config.LOCK_DIR / "db.lock"):
        conn = _connect()
        try:
            conn.execute(
                """
                insert into proposals
                    (id, agent, goal, scope, constraints, risk_level, state, policy, evidence, decision, commit, created_at, updated_at)
                values
                    (:id, :agent, :goal, :scope, :constraints, :risk_level, :state, :policy, :evidence, :decision, :commit, :created_at, :updated_at)
                on conflict(id) do update set
                    agent=excluded.agent,
                    goal=excluded.goal,
                    scope=excluded.scope,
                    constraints=excluded.constraints,
                    risk_level=excluded.risk_level,
                    state=excluded.state,
                    policy=excluded.policy,
                    evidence=excluded.evidence,
                    decision=excluded.decision,
                    commit_data=excluded.commit_data,
                    created_at=excluded.created_at,
                    updated_at=excluded.updated_at;
                """,
                {
                    "id": data.get("id"),
                    "agent": data.get("agent"),
                    "goal": data.get("goal"),
                    "scope": json.dumps(data.get("scope", []), ensure_ascii=False),
                    "constraints": json.dumps(data.get("constraints", []), ensure_ascii=False),
                    "risk_level": data.get("risk_level"),
                    "state": data.get("state"),
                    "policy": json.dumps(data.get("policy", {}), ensure_ascii=False),
                    "evidence": json.dumps(data.get("evidence", {}), ensure_ascii=False),
                    "decision": json.dumps(data.get("decision", {}), ensure_ascii=False),
                    "commit_data": json.dumps(data.get("commit", {}), ensure_ascii=False),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                },
            )
            conn.commit()
        finally:
            conn.close()


def list_events(limit: int = 50) -> list[Dict[str, Any]]:
    init_db()
    with file_lock(config.LOCK_DIR / "db.lock"):
        conn = _connect()
        try:
            cur = conn.execute(
                "select ts, event, proposal_id, actor, data from events order by id desc limit ?",
                (limit,),
            )
            rows = cur.fetchall()
        finally:
            conn.close()
    events = []
    for ts, event, pid, actor, data in rows:
        try:
            payload = json.loads(data) if data else {}
        except Exception:
            payload = {"raw": data}
        events.append(
            {"timestamp": ts, "event": event, "proposal_id": pid, "actor": actor, "data": payload}
        )
    return events
