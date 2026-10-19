"""Append-only plan snapshots and review events, scoped by tenant and hub."""

import json, sqlite3, os, threading
from datetime import datetime, timezone
from .core import ROOT

LOCK = threading.RLock()


def connection():
    path = os.environ.get("SAHRA_DB", str(ROOT / "outputs/state/plans.sqlite3"))
    from pathlib import Path

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute(
        "CREATE TABLE IF NOT EXISTS versions (id INTEGER PRIMARY KEY AUTOINCREMENT, tenant TEXT NOT NULL, hub TEXT NOT NULL, created TEXT NOT NULL, payload TEXT NOT NULL)"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, tenant TEXT, version INTEGER, created TEXT, payload TEXT)"
    )
    db.execute("CREATE INDEX IF NOT EXISTS tenant_versions ON versions(tenant,hub,id)")
    return db


def save(context, event):
    import copy

    context = copy.deepcopy(context)
    context["data"].pop("history", None)
    context["data"].pop("areas", None)
    cfg = context["cfg"]
    now = datetime.now(timezone.utc).isoformat()
    with LOCK, connection() as db:
        cursor = db.execute(
            "INSERT INTO versions(tenant,hub,created,payload) VALUES(?,?,?,?)",
            (cfg["client_id"], cfg["hub_id"], now, "{}"),
        )
        version = cursor.lastrowid
        context["plan"]["version"] = version
        context["plan"]["saved_at"] = now
        db.execute(
            "UPDATE versions SET payload=? WHERE id=?",
            (json.dumps(context, allow_nan=False), version),
        )
        db.execute(
            "INSERT INTO events(tenant,version,created,payload) VALUES(?,?,?,?)",
            (cfg["client_id"], version, now, json.dumps(event)),
        )
    return context["plan"]


def load(version, cfg, base):
    with connection() as db:
        row = db.execute(
            "SELECT payload FROM versions WHERE id=? AND tenant=? AND hub=?",
            (version, cfg["client_id"], cfg["hub_id"]),
        ).fetchone()
    if not row:
        raise KeyError("Plan version not found in active tenant/hub")
    context = json.loads(row[0])
    context["data"]["history"] = [
        h for h in base["history"] if h["date"] < context["cfg"]["plan_date"]
    ]
    context["data"]["areas"] = base["areas"]
    return context


def versions(cfg):
    with connection() as db:
        rows = db.execute(
            "SELECT id,created FROM versions WHERE tenant=? AND hub=? ORDER BY id DESC LIMIT 50",
            (cfg["client_id"], cfg["hub_id"]),
        ).fetchall()
    return [{"version": r[0], "created": r[1]} for r in rows]


def events(cfg):
    with connection() as db:
        rows = db.execute(
            "SELECT version,created,payload FROM events WHERE tenant=? ORDER BY id DESC LIMIT 100",
            (cfg["client_id"],),
        ).fetchall()
    return [{"version": r[0], "created": r[1], **json.loads(r[2])} for r in rows]
