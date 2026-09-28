"""CP1 — Config, Health, Logging."""
import json
import pytest

from app import config


def test_settings_has_six_fields():
    names = set(config.Settings.__dataclass_fields__)
    assert names == {
        "agent_api_key",
        "port",
        "redis_url",
        "log_level",
        "rate_limit_per_minute",
        "monthly_budget_usd",
    }


def test_api_key_has_no_default():
    with pytest.raises(TypeError):
        config.Settings()  # thiếu agent_api_key -> lỗi


def test_missing_secret_stops_app(monkeypatch):
    monkeypatch.setenv("AGENT_API_KEY", "")
    with pytest.raises(RuntimeError):
        config.load_settings()


def test_log_event_is_single_line_json(capsys):
    from app.logging_utils import log_event

    log_event("ask_completed", level="warning", user_id="sv01", cost_usd=0.0001)
    out = capsys.readouterr().out
    assert out.count("\n") == 1  # đúng một dòng
    record = json.loads(out)
    assert {"event", "level", "timestamp"} <= set(record)
    assert record["event"] == "ask_completed"
    assert record["user_id"] == "sv01"


def test_log_event_respects_log_level(capsys):
    from app.logging_utils import log_event

    log_event("noisy", level="debug")  # LOG_LEVEL=warning trong test
    assert capsys.readouterr().out == ""


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health_does_not_touch_redis(client, monkeypatch):
    from app import store

    def boom():
        raise AssertionError("/health không được gọi Redis")

    monkeypatch.setattr(store, "get_redis", boom)
    assert client.get("/health").status_code == 200
