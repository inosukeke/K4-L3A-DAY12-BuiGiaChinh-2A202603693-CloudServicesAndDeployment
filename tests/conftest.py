"""Test chạy offline: Redis giả (fakeredis) và API key cố định cho test."""
import os

# Phải đặt TRƯỚC khi import app.* vì settings được đọc lúc import.
os.environ["AGENT_API_KEY"] = "test-key-for-pytest"
os.environ["REDIS_URL"] = "fake://"
os.environ["LOG_LEVEL"] = "warning"
os.environ["RATE_LIMIT_PER_MINUTE"] = "5"
os.environ["MONTHLY_BUDGET_USD"] = "10.0"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import lifecycle, store  # noqa: E402
from app.main import app  # noqa: E402

API_KEY = os.environ["AGENT_API_KEY"]


@pytest.fixture(autouse=True)
def clean_state():
    store.reset_client()  # mỗi test một Redis giả mới, sạch dữ liệu
    lifecycle.reset()
    yield
    store.reset_client()
    lifecycle.reset()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth():
    def _headers(user="sv01"):
        return {"X-API-Key": API_KEY, "X-User-Id": user}

    return _headers
