"""Giới hạn chi phí theo tháng cho từng user; state nằm trong Redis."""
from datetime import datetime, timezone

from fastapi import HTTPException

from app.config import settings
from app.store import get_redis

# Giá mô phỏng (USD / 1K token), cùng mức gpt-4o-mini
PRICE_INPUT_PER_1K = 0.00015
PRICE_OUTPUT_PER_1K = 0.0006
_KEY_TTL_SECONDS = 35 * 24 * 3600  # sống qua hết tháng rồi tự dọn


def _key(user_id: str) -> str:
    return f"cost:{user_id}:{datetime.now(timezone.utc).strftime('%Y-%m')}"


def estimate_tokens(text: str) -> int:
    return max(1, len(text.split()) * 2)


def get_spent(user_id: str) -> float:
    return float(get_redis().get(_key(user_id)) or 0.0)


def check_budget(user_id: str) -> None:
    """Gọi TRƯỚC khi gọi LLM: đã hết ngân sách tháng thì trả 402."""
    if get_spent(user_id) >= settings.monthly_budget_usd:
        raise HTTPException(
            status_code=402,
            detail=f"Monthly budget of ${settings.monthly_budget_usd:g} exhausted",
        )


def record_cost(user_id: str, input_tokens: int, output_tokens: int) -> float:
    """Gọi SAU khi LLM trả kết quả: cộng chi phí thực tế của request."""
    cost = (input_tokens / 1000) * PRICE_INPUT_PER_1K + (
        output_tokens / 1000
    ) * PRICE_OUTPUT_PER_1K
    pipe = get_redis().pipeline()
    pipe.incrbyfloat(_key(user_id), cost)
    pipe.expire(_key(user_id), _KEY_TTL_SECONDS)
    pipe.execute()
    return cost
