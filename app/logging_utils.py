"""Log JSON: mỗi sự kiện đúng một dòng để hệ thống cloud thu log theo dòng."""
import json
import sys
from datetime import datetime, timezone

from app.config import settings

_LEVELS = {"debug": 10, "info": 20, "warning": 30, "error": 40}


def log_event(event: str, level: str = "info", **fields) -> None:
    level = level.lower()
    if _LEVELS.get(level, 20) < _LEVELS.get(settings.log_level, 20):
        return
    record = {
        "event": event,
        "level": level,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        **fields,
    }
    # default=str để một field không serialize được không làm hỏng cả request
    sys.stdout.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    sys.stdout.flush()
