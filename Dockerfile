# ============================================================
# Production Dockerfile: multi-stage, python slim, non-root
# Build từ root repo: docker build -t day12-agent:prod .
# ============================================================

# ---------- Stage 1: builder ----------
# Cài dependency vào virtualenv riêng để stage runtime chỉ copy đúng thứ cần chạy.
FROM python:3.11-slim AS builder

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements trước, cài xong mới copy code:
# đổi code không làm mất layer cache của bước cài dependency.
COPY requirements.txt .
RUN pip install --no-cache-dir --retries 10 --timeout 60 -r requirements.txt


# ---------- Stage 2: runtime ----------
FROM python:3.11-slim AS runtime

# User thường UID 10001, không chạy bằng root
RUN groupadd --gid 10001 agent \
    && useradd --uid 10001 --gid agent --no-create-home --shell /usr/sbin/nologin agent

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=agent:agent app/ ./app/
COPY --chown=agent:agent utils/ ./utils/

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

USER agent

EXPOSE 8000

# Liveness: chỉ gọi /health (không phụ thuộc Redis)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request as u; u.urlopen('http://localhost:%s/health' % os.getenv('PORT', '8000'), timeout=3)" || exit 1

# Shell form + exec: đọc ${PORT:-8000} và uvicorn vẫn là PID 1 nên nhận SIGTERM trực tiếp.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --timeout-graceful-shutdown 30"]
