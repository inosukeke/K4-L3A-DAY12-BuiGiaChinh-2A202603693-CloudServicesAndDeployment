"""CP3 — API Security: auth (401), rate limit (429), cost guard (402), thứ tự xử lý /ask."""
from app import store
from app.config import settings

Q = {"question": "Docker là gì?"}


def test_no_key_is_401(client):
    assert client.post("/ask", json=Q).status_code == 401


def test_wrong_key_is_401(client):
    r = client.post("/ask", json=Q, headers={"X-API-Key": "sai-roi"})
    assert r.status_code == 401


def test_non_ascii_key_is_401_not_500(client):
    r = client.post("/ask", json=Q, headers={"X-API-Key": "khóa-lạ".encode()})
    assert r.status_code == 401


def test_valid_key_is_200(client, auth):
    r = client.post("/ask", json=Q, headers=auth())
    assert r.status_code == 200
    body = r.json()
    assert body["answer"]
    assert body["user_id"] == "sv01"


def test_default_user_when_header_missing(client):
    r = client.post("/ask", json=Q, headers={"X-API-Key": settings.agent_api_key})
    assert r.status_code == 200
    assert r.json()["user_id"] == "anonymous"


def test_bad_user_id_rejected(client):
    r = client.post(
        "/ask",
        json=Q,
        headers={"X-API-Key": settings.agent_api_key, "X-User-Id": "a:b*c"},
    )
    assert r.status_code == 400


def test_rate_limit_429_after_limit(client, auth):
    limit = settings.rate_limit_per_minute
    codes = [client.post("/ask", json=Q, headers=auth()).status_code for _ in range(limit + 2)]
    assert codes[:limit] == [200] * limit
    assert codes[limit:] == [429, 429]


def test_rate_limit_is_per_user(client, auth):
    for _ in range(settings.rate_limit_per_minute):
        client.post("/ask", json=Q, headers=auth("a"))
    assert client.post("/ask", json=Q, headers=auth("a")).status_code == 429
    assert client.post("/ask", json=Q, headers=auth("b")).status_code == 200


def test_rate_limit_uses_sorted_set_with_ttl(client, auth):
    client.post("/ask", json=Q, headers=auth())
    r = store.get_redis()
    assert r.type("rate:sv01") == "zset"
    assert 0 < r.ttl("rate:sv01") <= 61


def test_rate_limit_members_unique_for_same_timestamp(client, auth, monkeypatch):
    import time

    monkeypatch.setattr(time, "time", lambda: 1_000_000.0)  # mọi request cùng timestamp
    monkeypatch.setattr(settings, "rate_limit_per_minute", 100)
    for _ in range(3):
        client.post("/ask", json=Q, headers=auth())
    assert store.get_redis().zcard("rate:sv01") == 3


def test_cost_recorded_in_monthly_key(client, auth):
    from datetime import datetime, timezone

    client.post("/ask", json=Q, headers=auth())
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    assert float(store.get_redis().get(f"cost:sv01:{month}")) > 0


def test_budget_exceeded_is_402(client, auth, monkeypatch):
    monkeypatch.setattr(settings, "monthly_budget_usd", 0.00002)  # ~2 request
    codes = [client.post("/ask", json=Q, headers=auth()).status_code for _ in range(5)]
    assert codes[0] == 200  # lần đầu còn ngân sách
    assert 402 in codes  # sau khi ghi nhận chi phí thì hết


def test_budget_checked_before_llm(client, auth, monkeypatch):
    from app import main

    monkeypatch.setattr(settings, "monthly_budget_usd", 0.0)
    called = []
    monkeypatch.setattr(main, "llm_ask", lambda q: called.append(q) or "x")
    assert client.post("/ask", json=Q, headers=auth()).status_code == 402
    assert called == []  # LLM không được gọi khi đã hết ngân sách


def test_auth_runs_before_rate_limit(client, monkeypatch):
    from app import main

    called = []
    monkeypatch.setattr(main, "check_rate_limit", lambda u: called.append(u))
    assert client.post("/ask", json=Q).status_code == 401
    assert called == []


def test_empty_question_is_422(client, auth):
    assert client.post("/ask", json={"question": ""}, headers=auth()).status_code == 422
