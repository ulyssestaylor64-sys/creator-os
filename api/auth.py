"""
Creator OS — 账号鉴权基础能力
只用标准库：PBKDF2 密码哈希 + 随机会话令牌。
"""
import hashlib
import hmac
import re
import secrets

PBKDF2_ITERATIONS = 200_000
SESSION_DAYS = 30
SESSION_COOKIE = "cos_session"
DEVICE_COOKIE = "cos_device"

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email)) and len(email) <= 120


def valid_password(password: str) -> bool:
    return isinstance(password, str) and 8 <= len(password) <= 128


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS
    ).hex()
    return "pbkdf2_sha256${}${}${}".format(PBKDF2_ITERATIONS, salt, digest)


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt, digest = (stored or "").split("$")
        if algo != "pbkdf2_sha256":
            return False
        calc = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations)
        ).hex()
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(calc, digest)


def new_token() -> str:
    """生成会话令牌（只返回给客户端一次，服务端存哈希）。"""
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_user_id() -> str:
    return "u_" + secrets.token_hex(8)


def new_device_id() -> str:
    return "dev_" + secrets.token_hex(8)
