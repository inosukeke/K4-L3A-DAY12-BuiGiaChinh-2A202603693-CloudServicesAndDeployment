"""Xác thực bằng API key trong header X-API-Key."""
import re
import secrets

from fastapi import Header, HTTPException

from app.config import settings

DEFAULT_USER_ID = "anonymous"
_USER_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")


def authenticate(
    x_api_key: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
) -> str:
    """Trả về user_id nếu key hợp lệ; 401 nếu thiếu hoặc sai key."""
    # compare_digest so sánh constant-time, tránh lộ khóa qua timing attack.
    # Encode sang bytes để header có ký tự non-ASCII không làm compare_digest văng TypeError.
    provided = (x_api_key or "").encode()
    expected = settings.agent_api_key.encode()
    if not x_api_key or not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Include header: X-API-Key: <key>",
        )
    user_id = x_user_id or DEFAULT_USER_ID
    # user_id đi vào key Redis nên chỉ chấp nhận ký tự an toàn
    if not _USER_ID_RE.match(user_id):
        raise HTTPException(status_code=400, detail="Invalid X-User-Id")
    return user_id
