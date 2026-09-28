"""Sliding window 60 giây bằng Redis Sorted Set (score = thời điểm request)."""
import time
import uuid

from fastapi import HTTPException

from app.config import settings
from app.store import get_redis

WINDOW_SECONDS = 60


def check_rate_limit(user_id: str) -> None:
    r = get_redis()
    key = f"rate:{user_id}"
    now = time.time()

    # 1) xóa request cũ  2) đếm request còn lại
    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, now - WINDOW_SECONDS)
    pipe.zcard(key)
    _, count = pipe.execute()

    # 3) kiểm tra giới hạn
    if count >= settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {settings.rate_limit_per_minute} req/min",
            headers={"Retry-After": str(WINDOW_SECONDS)},
        )

    # 4) thêm request mới (member duy nhất, nếu không 2 request cùng timestamp sẽ đè nhau)
    # 5) đặt TTL để key của user không hoạt động tự biến mất
    pipe = r.pipeline()
    pipe.zadd(key, {f"{now}:{uuid.uuid4().hex}": now})
    pipe.expire(key, WINDOW_SECONDS + 1)
    pipe.execute()
