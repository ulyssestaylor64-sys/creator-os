"""
Creator OS — 轻量持久化层（SQLite）
只保存用户产生的数据：评论规则、收藏选题、AI 草稿、导入的爆款。
注意：Render 免费实例的文件系统是临时的，实例重启/重新部署后数据库会重置；
如需长期保存，请挂载 Render Disk 或改用 Postgres（接口不变）。
"""
import json
import os
import sqlite3
from datetime import datetime
from typing import Any

_DEFAULT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.getenv("CREATOROS_DB", os.path.join(_DEFAULT_DIR, "creatoros.db"))


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS comment_rules (
            id TEXT PRIMARY KEY,
            keyword TEXT NOT NULL,
            category TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            backfill_count INTEGER NOT NULL DEFAULT 0,
            applied_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS saved_topics (
            topic_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            note TEXT DEFAULT '',
            saved_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id TEXT NOT NULL,
            type TEXT NOT NULL,
            model TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS imported_hits (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ---------- 评论分类规则 ----------
def list_rules() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM comment_rules ORDER BY applied_at DESC").fetchall()
    return [dict(r) for r in rows]


def add_rule(rule: dict) -> dict:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO comment_rules (id, keyword, category, status, backfill_count, applied_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (rule["id"], rule["keyword"], rule["category"], rule.get("status", "active"),
             rule.get("backfill_count", 0), rule.get("applied_at", _now())),
        )
    return rule


# ---------- 收藏选题 ----------
def save_topic(topic_id: str, title: str, note: str = "") -> dict:
    row = {"topic_id": topic_id, "title": title, "note": note, "saved_at": _now()}
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO saved_topics (topic_id, title, note, saved_at) VALUES (?, ?, ?, ?)",
            (topic_id, title, note, row["saved_at"]),
        )
    return row


def list_saved_topics() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM saved_topics ORDER BY saved_at DESC").fetchall()
    return [dict(r) for r in rows]


def delete_saved_topic(topic_id: str) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM saved_topics WHERE topic_id = ?", (topic_id,))
    return cur.rowcount > 0


# ---------- AI 草稿 ----------
def save_draft(topic_id: str, draft_type: str, model: str, content: Any) -> int:
    payload = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO drafts (topic_id, type, model, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (topic_id, draft_type, model, payload, _now()),
        )
    return cur.lastrowid


def list_drafts(limit: int = 20) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, topic_id, type, model, content, created_at FROM drafts ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    out = []
    for r in rows:
        item = dict(r)
        try:
            item["content"] = json.loads(item["content"])
        except (TypeError, ValueError):
            pass
        out.append(item)
    return out


# ---------- 导入的爆款 ----------
def save_imported_hit(hit: dict) -> dict:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO imported_hits (id, title, payload, created_at) VALUES (?, ?, ?, ?)",
            (hit["id"], hit["title"], json.dumps(hit, ensure_ascii=False), _now()),
        )
    return hit


def list_imported_hits() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute("SELECT payload FROM imported_hits ORDER BY created_at DESC").fetchall()
    out = []
    for r in rows:
        try:
            out.append(json.loads(r["payload"]))
        except ValueError:
            continue
    return out


init_db()
