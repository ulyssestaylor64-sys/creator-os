"""
Creator OS — 轻量持久化层（SQLite / Postgres 双模式）

只保存用户产生的数据：账号、会话、评论规则、收藏选题、AI 草稿、导入的爆款。
所有用户数据按 owner 隔离：登录用户为 u_xxx，未登录设备为 dev_xxx。

模式选择：
- 设置 DATABASE_URL=postgres://... 时走 Postgres（Render Postgres、Supabase 等）；
- 未设置时走本地 SQLite，路径可用 CREATOROS_DB 指定（Render 挂载磁盘场景）。
两种模式的接口与表结构一致，业务代码不需要区分。
"""
import json
import os
import shutil
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlsplit

_DEFAULT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.getenv("CREATOROS_DB", os.path.join(_DEFAULT_DIR, "creatoros.db"))

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
IS_PG = DATABASE_URL.startswith(("postgres://", "postgresql://"))


# ---------- 连接层：统一 SQLite 与 Postgres 的调用方式 ----------
def _to_pg(sql: str) -> str:
    """把 SQLite 的 ? 占位符换成 psycopg2 的 %s（本文件 SQL 不含字符串内 ?）。"""
    return sql.replace("?", "%s")


class _PgCursor:
    """把 psycopg2 游标包装成与 sqlite3 游标相近的行为。"""

    def __init__(self, cur):
        self._cur = cur

    def fetchone(self):
        row = self._cur.fetchone()
        return dict(row) if row else None

    def fetchall(self):
        return [dict(r) for r in self._cur.fetchall()]

    @property
    def rowcount(self) -> int:
        return self._cur.rowcount

    @property
    def lastrowid(self):
        return None


class _PgConn:
    """psycopg2 连接包装：提供 execute() 与 with 语义（提交/回滚后关闭）。"""

    def __init__(self, raw):
        self._raw = raw

    def execute(self, sql: str, params=()):
        from psycopg2.extras import RealDictCursor

        cur = self._raw.cursor(cursor_factory=RealDictCursor)
        cur.execute(_to_pg(sql), params)
        return _PgCursor(cur)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self._raw.rollback()
        else:
            self._raw.commit()
        self._raw.close()
        return False


def _connect():
    if IS_PG:
        try:
            import psycopg2
        except ImportError as exc:  # pragma: no cover - 依赖缺失时给出明确提示
            raise RuntimeError(
                "检测到 DATABASE_URL 但未安装 psycopg2，请执行 pip install psycopg2-binary"
            ) from exc
        return _PgConn(psycopg2.connect(DATABASE_URL, connect_timeout=10))

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    # 多设备并发写入时降低锁冲突
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
    except sqlite3.DatabaseError:
        pass
    return conn


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _columns(conn, table: str) -> list[str]:
    if IS_PG:
        rows = conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = ?", (table,)
        ).fetchall()
        return [r["column_name"] for r in rows]
    return [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def _table_exists(conn, table: str) -> bool:
    if IS_PG:
        row = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_name = ?", (table,)
        ).fetchone()
        return row is not None
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def _needs_user_scope(conn) -> bool:
    """旧库（无 user_id）需要一次迁移。"""
    for table in ("comment_rules", "saved_topics", "drafts", "imported_hits"):
        if _table_exists(conn, table) and "user_id" not in _columns(conn, table):
            return True
    return False


def _migrate_user_scope(conn) -> None:
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


def _schema() -> str:
    drafts_id = "BIGSERIAL PRIMARY KEY" if IS_PG else "INTEGER PRIMARY KEY AUTOINCREMENT"
    return f"""
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
            id {drafts_id},
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
        """


def _init_once() -> None:
    with _connect() as conn:
        if IS_PG:
            for stmt in [s.strip() for s in _schema().split(";") if s.strip()]:
                conn.execute(stmt)
        else:
            conn.executescript(_schema())
            if _needs_user_scope(conn):
                # 迁移前先备份，回滚时直接还原这个文件
                if os.path.exists(DB_PATH):
                    shutil.copy2(DB_PATH, DB_PATH + ".bak")
                _migrate_user_scope(conn)


def init_db() -> None:
    """启动时建表。外部数据库可能短暂不可达，重试 3 次再失败退出。"""
    last_error = None
    for attempt in range(3):
        try:
            _init_once()
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"数据库初始化失败：{last_error}")


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
            "INSERT INTO sessions (token_hash, user_id, created_at, expires_at)"
            " VALUES (?, ?, ?, ?)"
            " ON CONFLICT (token_hash) DO UPDATE SET"
            " user_id = excluded.user_id, created_at = excluded.created_at,"
            " expires_at = excluded.expires_at",
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
            "INSERT INTO comment_rules"
            " (user_id, id, keyword, category, status, backfill_count, applied_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT (user_id, id) DO UPDATE SET"
            " keyword = excluded.keyword, category = excluded.category,"
            " status = excluded.status, backfill_count = excluded.backfill_count,"
            " applied_at = excluded.applied_at",
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
            "INSERT INTO saved_topics (user_id, topic_id, title, note, saved_at)"
            " VALUES (?, ?, ?, ?, ?)"
            " ON CONFLICT (user_id, topic_id) DO UPDATE SET"
            " title = excluded.title, note = excluded.note, saved_at = excluded.saved_at",
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
        row = conn.execute(
            "INSERT INTO drafts (user_id, topic_id, type, model, content, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?) RETURNING id",
            (owner, topic_id, draft_type, model, payload, _now()),
        ).fetchone()
    return int(row["id"]) if row else 0


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
            "INSERT INTO imported_hits (user_id, id, title, payload, created_at)"
            " VALUES (?, ?, ?, ?, ?)"
            " ON CONFLICT (user_id, id) DO UPDATE SET"
            " title = excluded.title, payload = excluded.payload,"
            " created_at = excluded.created_at",
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


def _pg_target() -> str:
    """只暴露 host/dbname，避免把密码写进健康检查。"""
    parts = urlsplit(DATABASE_URL)
    host = parts.hostname or "unknown"
    db = (parts.path or "/").lstrip("/") or "unknown"
    return f"{host}/{db}"


def db_status() -> dict:
    """运行状态：用于确认数据落在哪里、是否可写。"""
    if IS_PG:
        info = {"backend": "postgres", "target": _pg_target(), "persistent": True,
                "path": _pg_target(), "writable": True, "exists": True, "size_bytes": 0}
    else:
        info = {
            "backend": "sqlite",
            "path": DB_PATH,
            "exists": os.path.exists(DB_PATH),
            "persistent": os.getenv("CREATOROS_PERSISTENT", "") == "1",
            "writable": os.access(os.path.dirname(DB_PATH), os.W_OK),
            "size_bytes": os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0,
        }
    try:
        with _connect() as conn:
            info["users"] = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
            info["saved_topics"] = conn.execute("SELECT COUNT(*) AS c FROM saved_topics").fetchone()["c"]
            if not IS_PG:
                info["journal_mode"] = conn.execute("PRAGMA journal_mode").fetchone()[0]
        info["ok"] = True
    except Exception as exc:  # noqa: BLE001
        info["ok"] = False
        info["error"] = str(exc)
    return info


init_db()
