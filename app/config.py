"""Cấu hình theo 12-Factor: mọi giá trị đọc từ biến môi trường.

Sáu trường của Settings:
  port                  - PORT (mặc định 8000; cloud tự cấp)
  redis_url             - REDIS_URL
  agent_api_key         - AGENT_API_KEY (secret, KHÔNG có mặc định)
  log_level             - LOG_LEVEL
  rate_limit_per_minute - RATE_LIMIT_PER_MINUTE
  monthly_budget_usd    - MONTHLY_BUDGET_USD
"""
import os
from dataclasses import dataclass

try:  # chỉ tiện cho chạy local; trên cloud/Docker biến env đã có sẵn
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


@dataclass
class Settings:
    agent_api_key: str  # secret: bắt buộc truyền vào, không có default
    port: int = 8000
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "info"
    rate_limit_per_minute: int = 10
    monthly_budget_usd: float = 10.0


def load_settings() -> Settings:
    api_key = os.getenv("AGENT_API_KEY", "").strip()
    if not api_key:
        # Dừng ngay thay vì chạy với khóa yếu/rỗng.
        raise RuntimeError(
            "AGENT_API_KEY chưa được đặt. Tạo khóa bằng: "
            'python -c "import secrets; print(secrets.token_urlsafe(32))"'
        )
    return Settings(
        agent_api_key=api_key,
        port=int(os.getenv("PORT", "8000")),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
        rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "10")),
        monthly_budget_usd=float(os.getenv("MONTHLY_BUDGET_USD", "10.0")),
    )


settings = load_settings()
