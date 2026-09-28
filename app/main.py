"""AI Agent production-ready: auth, rate limit, cost guard, Redis state, health/ready, graceful shutdown."""
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import redis
import uvicorn
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app import lifecycle
from app.auth import authenticate
from app.config import settings
from app.cost_guard import check_budget, estimate_tokens, record_cost
from app.logging_utils import log_event
from app.rate_limiter import check_rate_limit
from app.store import append_message, get_history, ping
from utils.mock_llm import ask as llm_ask

APP_VERSION = "1.0.0"
START_TIME = time.time()
# Trong container HOSTNAME = container id, giúp thấy request đi vào instance nào khi scale
INSTANCE_ID = os.getenv("HOSTNAME", "local")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Phải đăng ký SAU khi Uvicorn đã cài handler của nó (Uvicorn cài lúc serve(),
    # sau khi import app), để handler cũ mình lưu lại chính là handler của Uvicorn.
    try:
        lifecycle.install_signal_handlers()  # SIGTERM / SIGINT
    except ValueError:  # không phải main thread (vd. TestClient) thì bỏ qua
        pass
    log_event("startup", version=APP_VERSION, instance=INSTANCE_ID)
    yield
    lifecycle.shutting_down = True
    log_event("shutdown", instance=INSTANCE_ID)


app = FastAPI(title="Production AI Agent", version=APP_VERSION, lifespan=lifespan)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


@app.middleware("http")
async def access_log(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    level = "debug" if request.url.path in ("/health", "/ready") else "info"
    log_event(
        "request",
        level=level,
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        ms=round((time.perf_counter() - start) * 1000, 1),
    )
    return response


@app.exception_handler(redis.exceptions.RedisError)
async def redis_unavailable(request: Request, exc: redis.exceptions.RedisError):
    # Redis chết thì rate limit / cost guard không còn đáng tin: từ chối (fail closed)
    log_event("redis_error", level="error", error=type(exc).__name__)
    return JSONResponse(status_code=503, content={"detail": "Storage unavailable"})


@app.get("/")
def root():
    return {
        "app": "Production AI Agent",
        "version": APP_VERSION,
        "endpoints": {
            "ask": "POST /ask (X-API-Key, X-User-Id)",
            "health": "GET /health",
            "ready": "GET /ready",
        },
    }


@app.get("/health")
def health():
    """Liveness: chỉ cho biết process còn sống. KHÔNG gọi Redis hay dependency ngoài."""
    if lifecycle.is_shutting_down():
        return JSONResponse(status_code=503, content={"status": "shutting_down"})
    return {
        "status": "ok",
        "version": APP_VERSION,
        "instance": INSTANCE_ID,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready")
def ready():
    """Readiness: có nhận request mới được không (không shutdown và Redis sống)."""
    if lifecycle.is_shutting_down():
        return JSONResponse(
            status_code=503, content={"ready": False, "reason": "shutting_down"}
        )
    redis_ok = ping()
    if not redis_ok:
        return JSONResponse(
            status_code=503, content={"ready": False, "redis": False}
        )
    return {"ready": True, "redis": True}


@app.post("/ask")
def ask(body: AskRequest, user_id: str = Depends(authenticate)):
    """Xác thực (Depends) -> rate limit -> cost guard -> history -> LLM -> lưu -> cost -> log."""
    check_rate_limit(user_id)
    check_budget(user_id)

    history = get_history(user_id)
    answer = llm_ask(body.question)

    append_message(user_id, "user", body.question)
    append_message(user_id, "assistant", answer)

    cost = record_cost(
        user_id, estimate_tokens(body.question), estimate_tokens(answer)
    )
    log_event(
        "ask_completed",
        user_id=user_id,
        cost_usd=round(cost, 6),
        history_messages=len(history),
        instance=INSTANCE_ID,
    )
    return {
        "question": body.question,
        "answer": answer,
        "user_id": user_id,
        "history_messages": len(history),  # số message đã có TRƯỚC lượt này
        "served_by": INSTANCE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        timeout_graceful_shutdown=30,
    )
