"""Redis store: state dùng chung giữa các instance (conversation history)."""
import json
from datetime import datetime, timezone

import redis

from app.config import settings

HISTORY_MAX_MESSAGES = 20  # 10 lượt hỏi-đáp gần nhất
HISTORY_TTL_SECONDS = 3600  # lịch sử cũ tự hết hạn sau 1 giờ không hoạt động

_client = None


def get_redis():
    global _client
    if _client is None:
        if settings.redis_url.startswith("fake://"):
            import fakeredis  # chỉ dùng khi chưa có Docker/Redis

            _client = fakeredis.FakeStrictRedis(decode_responses=True)
        else:
            _client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
    return _client


def reset_client() -> None:
    global _client
    _client = None


def ping() -> bool:
    try:
        return bool(get_redis().ping())
    except Exception:
        return False


def _history_key(user_id: str) -> str:
    return f"history:{user_id}"


def get_history(user_id: str) -> list[dict]:
    raw = get_redis().lrange(_history_key(user_id), 0, -1)
    return [json.loads(item) for item in raw]


def append_message(user_id: str, role: str, content: str) -> None:
    key = _history_key(user_id)
    message = {
        "role": role,
        "content": content,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    pipe = get_redis().pipeline()
    pipe.rpush(key, json.dumps(message, ensure_ascii=False))
    pipe.ltrim(key, -HISTORY_MAX_MESSAGES, -1)  # chỉ giữ N message gần nhất
    pipe.expire(key, HISTORY_TTL_SECONDS)
    pipe.execute()
