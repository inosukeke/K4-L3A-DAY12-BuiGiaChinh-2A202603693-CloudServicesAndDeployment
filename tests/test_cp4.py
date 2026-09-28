"""CP4 — Scaling & Reliability: state trong Redis, /ready, graceful shutdown."""
import signal

from app import lifecycle, store
from app.store import HISTORY_MAX_MESSAGES

Q = {"question": "Hello"}


def test_history_persists_in_redis(client, auth):
    client.post("/ask", json=Q, headers=auth())
    r = client.post("/ask", json=Q, headers=auth())
    assert r.json()["history_messages"] == 2  # user + assistant của lượt trước
    assert store.get_redis().llen("history:sv01") == 4


def test_history_survives_new_app_state(client, auth):
    """Mô phỏng instance khác: cắt bỏ client Redis trong process, dữ liệu vẫn nằm ở Redis."""
    client.post("/ask", json=Q, headers=auth())
    redis_client = store.get_redis()
    store.reset_client()
    store._client = redis_client  # instance mới nối cùng một Redis
    assert len(store.get_history("sv01")) == 2


def test_history_trimmed_and_ttl(client, auth, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "rate_limit_per_minute", 1000)
    for _ in range(HISTORY_MAX_MESSAGES):  # sinh nhiều hơn giới hạn
        client.post("/ask", json=Q, headers=auth())
    r = store.get_redis()
    assert r.llen("history:sv01") == HISTORY_MAX_MESSAGES
    assert r.ttl("history:sv01") > 0


def test_no_global_history_dict():
    from app import main

    assert not any(
        isinstance(v, dict) and "history" in name.lower()
        for name, v in vars(main).items()
    )


def test_ping_true_and_false(monkeypatch):
    assert store.ping() is True

    class Broken:
        def ping(self):
            raise ConnectionError("down")

    monkeypatch.setattr(store, "_client", Broken())
    assert store.ping() is False  # bắt exception, không văng ra ngoài


def test_ready_ok(client):
    r = client.get("/ready")
    assert r.status_code == 200
    assert r.json()["redis"] is True


def test_redis_down_health_200_ready_503(client, monkeypatch):
    monkeypatch.setattr(store, "ping", lambda: False)
    from app import main

    monkeypatch.setattr(main, "ping", lambda: False)
    assert client.get("/health").status_code == 200
    r = client.get("/ready")
    assert r.status_code == 503
    assert r.json()["redis"] is False


def test_shutting_down_both_503(client):
    lifecycle.shutting_down = True
    assert client.get("/health").status_code == 503
    assert client.get("/ready").status_code == 503


def test_redis_down_on_ask_is_503(client, auth, monkeypatch):
    import redis as redis_lib

    class Broken:
        def pipeline(self):
            raise redis_lib.exceptions.ConnectionError("down")

    monkeypatch.setattr(store, "_client", Broken())
    assert client.post("/ask", json=Q, headers=auth()).status_code == 503


def test_signal_handler_sets_flag_and_calls_previous():
    calls = []
    saved = {s: signal.getsignal(s) for s in (signal.SIGTERM, signal.SIGINT)}
    try:
        def old(signum, frame):
            calls.append(signum)

        signal.signal(signal.SIGTERM, old)
        signal.signal(signal.SIGINT, old)
        lifecycle._previous_handlers.clear()
        lifecycle.install_signal_handlers()

        assert signal.getsignal(signal.SIGTERM) is not old  # đã được thay
        signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)  # gọi handler mới
        assert lifecycle.is_shutting_down()
        assert calls == [signal.SIGTERM]  # handler cũ vẫn được gọi tiếp
    finally:
        for s, h in saved.items():
            signal.signal(s, h)
        lifecycle._previous_handlers.clear()


def test_signal_handler_ignores_non_callable_previous():
    saved = {s: signal.getsignal(s) for s in (signal.SIGTERM, signal.SIGINT)}
    try:
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        lifecycle._previous_handlers.clear()
        lifecycle.install_signal_handlers()
        signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)  # không được văng lỗi
        assert lifecycle.is_shutting_down()
    finally:
        for s, h in saved.items():
            signal.signal(s, h)
        lifecycle._previous_handlers.clear()
