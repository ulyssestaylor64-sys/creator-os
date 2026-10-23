"""
Creator OS — 轻量持久化层（SQLite）

只保存用户产生的数据：账号、会话、评论规则、收藏选题、AI 草稿、导入的爆款。
所有用户数据按 owner 隔离：登录用户为 u_xxx，未登录设备为 dev_xxx。

注意：Render 免费实例的文件系统是临时的，实例重启/重新部署后数据库会重置；
如需长期保存，请挂载 Render Disk 或改用 Postgres（接口不变）。
"""
import json
import os
import shutil
import sqlite3
from datetime import datetime, timedelta
from typing import Any

_DEFAULT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.getenv("CREATOROS_DB", os.path.join(_DEFAULT_DIR, "creatoros.db"))


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def _needs_user_scope(conn: sqlite3.Connection) -> bool:
    """旧库（无 user_id）需要一次迁移。"""
    for table in ("comment_rules", "saved_topics", "drafts", "imported_hits"):
        if _table_exists(conn, table) and "user_id" not in _columns(conn, table):
            return True
    return False


def _migrate_user_scope(conn: sqlite3.Connection) -> None:
    """为旧表补 user_id；按用户隔离的表改为复合主键，避免不同账号互相覆盖。"""
    if _table_exists(conn, "comment_rules") and "user_id" not in _columns(conn, "comment_rules"):
        conn.executescript("""
        CREATE TABLE comment_rules_new (
            user_id TEXT NOT NULL DEFAULT '',
            id TEXT NOT NULL,
            keyword TEXT NOT NULL,
            category TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            backfill_count INTEGER NOT NULL DEFAULT 0,
            applied_at TEXT NOT NULL,
            PRIMARY KEY (user_id, id)
        );
        INSERT INTO comment_rules_new (user_id, id, keyword, category, status, backfill_count, applied_at)
            SELECT '', id, keyword, category, status, backfill_count, applied_at FROM comment_rules;
        DROP TABLE comment_rules;
        ALTER TABLE comment_rules_new RENAME TO comment_rules;
        """)

    if _table_exists(conn, "drafts") and "user_id" not in _columns(conn, "drafts"):
        conn.execute("ALTER TABLE drafts ADD COLUMN user_id TEXT NOT NULL DEFAULT ''")

    if _table_exists(conn, "saved_topics") and "user_id" not in _columns(conn, "saved_topics"):
        conn.executescript("""
        CREATE TABLE saved_topics_new (
            user_id TEXT NOT NULL DEFAULT '',
            topic_id TEXT NOT NULL,
            title TEXT NOT NULL,
            note TEXT DEFAULT '',
            saved_at TEXT NOT NULL,
            PRIMARY KEY (user_id, topic_id)
        );
        INSERT INTO saved_topics_new (user_id, topic_id, title, note, saved_at)
            SELECT '', topic_id, title, note, saved_at FROM saved_topics;
        DROP TABLE saved_topics;
        ALTER TABLE saved_topics_new RENAME TO saved_topics;
        """)

    if _table_exists(conn, "imported_hits") and "user_id" not in _columns(conn, "imported_hits"):
        conn.executescript("""
        CREATE TABLE imported_hits_new (
            user_id TEXT NOT NULL DEFAULT '',
            id TEXT NOT NULL,
            title TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (user_id, id)
        );
        INSERT INTO imported_hits_new (user_id, id, title, payload, created_at)
            SELECT '', id, title, payload, created_at FROM imported_hits;
        DROP TABLE imported_hits;
        ALTER TABLE imported_hits_new RENAME TO imported_hits;
        """)


def init_db() -> None:
    with _connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);

        CREATE TABLE IF NOT EXISTS comment_rules (
            user_id TEXT NOT NULL DEFAULT '',
            id TEXT NOT NULL,
            keyword TEXT NOT NULL,
            category TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            backfill_count INTEGER NOT NULL DEFAULT 0,
            applied_at TEXT NOT NULL,
            PRIMARY KEY (user_id, id)
        );
        CREATE TABLE IF NOT EXISTS saved_topics (
            user_id TEXT NOT NULL DEFAULT '',
            topic_id TEXT NOT NULL,
            title TEXT NOT NULL,
            note TEXT DEFAULT '',
            saved_at TEXT NOT NULL,
            PRIMARY KEY (user_id, topic_id)
        );
        CREATE TABLE IF NOT EXISTS drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL DEFAULT '',
            topic_id TEXT NOT NULL,
            type TEXT NOT NULL,
            model TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS imported_hits (
            user_id TEXT NOT NULL DEFAULT '',
            id TEXT NOT NULL,
            title TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (user_id, id)
        );
        """)

        if _needs_user_scope(conn):
            # 迁移前先备份，回滚时直接还原这个文件
            if os.path.exists(DB_PATH):
                shutil.copy2(DB_PATH, DB_PATH + ".bak")
            _migrate_user_scope(conn)


# ---------- 账号 ----------
def create_user(user_id: str, email: str, password_hash: str) -> dict:
    row = {"id": user_id, "email": email, "password_hash": password_hash, "created_at": _now()}
    with _connect() as conn:
        conn.execute(
            "INSERT INTO users (id, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (user_id, email, password_hash, row["created_at"]),
        )
    return {"id": user_id, "email": email, "created_at": row["created_at"]}


def get_user_by_email(email: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


# ---------- 会话 ----------
def create_session(token_hash: str, user_id: str, days: int = 30) -> str:
    created = datetime.now()
    expires = created + timedelta(days=days)
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO sessions (token_hash, user_id, created_at, expires_at)"
            " VALUES (?, ?, ?, ?)",
            (token_hash, user_id, created.isoformat(timespec="seconds"),
             expires.isoformat(timespec="seconds")),
        )
    return expires.isoformat(timespec="seconds")


def get_session_user(token_hash: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT s.user_id, s.expires_at, u.email FROM sessions s"
            " JOIN users u ON u.id = s.user_id WHERE s.token_hash = ?",
            (token_hash,),
        ).fetchone()
        if not row:
            return None
        if datetime.fromisoformat(row["expires_at"]) <= datetime.now():
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
            return None
    return {"id": row["user_id"], "email": row["email"]}


def delete_session(token_hash: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))


def purge_expired_sessions() -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (_now(),))


# ---------- 评论分类规则 ----------
def list_rules(owner: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM comment_rules WHERE user_id = ? ORDER BY applied_at DESC", (owner,)
        ).fetchall()
    return [dict(r) for r in rows]


def add_rule(owner: str, rule: dict) -> dict:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO comment_rules"
            " (user_id, id, keyword, category, status, backfill_count, applied_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (owner, rule["id"], rule["keyword"], rule["category"],
             rule.get("status", "active"), rule.get("backfill_count", 0),
             rule.get("applied_at", _now())),
        )
    return rule


# ---------- 收藏选题 ----------
def save_topic(owner: str, topic_id: str, title: str, note: str = "") -> dict:
    row = {"user_id": owner, "topic_id": topic_id, "title": title, "note": note, "saved_at": _now()}
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO saved_topics (user_id, topic_id, title, note, saved_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (owner, topic_id, title, note, row["saved_at"]),
        )
    return row


def list_saved_topics(owner: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM saved_topics WHERE user_id = ? ORDER BY saved_at DESC", (owner,)
        ).fetchall()
    return [dict(r) for r in rows]


def delete_saved_topic(owner: str, topic_id: str) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM saved_topics WHERE user_id = ? AND topic_id = ?", (owner, topic_id)
        )
    return cur.rowcount > 0


# ---------- AI 草稿 ----------
def save_draft(owner: str, topic_id: str, draft_type: str, model: str, content: Any) -> int:
    payload = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO drafts (user_id, topic_id, type, model, content, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (owner, topic_id, draft_type, model, payload, _now()),
        )
    return cur.lastrowid


def list_drafts(owner: str, limit: int = 20) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, topic_id, type, model, content, created_at FROM drafts"
            " WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (owner, limit),
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
def save_imported_hit(owner: str, hit: dict) -> dict:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO imported_hits (user_id, id, title, payload, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (owner, hit["id"], hit["title"], json.dumps(hit, ensure_ascii=False), _now()),
        )
    return hit


def list_imported_hits(owner: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT payload FROM imported_hits WHERE user_id = ? ORDER BY created_at DESC", (owner,)
        ).fetchall()
    out = []
    for r in rows:
        try:
            out.append(json.loads(r["payload"]))
        except ValueError:
            continue
    return out


init_db()
