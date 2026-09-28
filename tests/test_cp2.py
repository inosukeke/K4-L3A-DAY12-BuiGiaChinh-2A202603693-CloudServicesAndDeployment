"""CP2 — Docker. Phần đọc file chạy offline; phần build/run cần Docker daemon (marker docker)."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = (ROOT / "Dockerfile").read_text(encoding="utf-8")


def test_multi_stage_slim():
    assert len(re.findall(r"^FROM ", DOCKERFILE, re.M)) >= 2
    assert "AS builder" in DOCKERFILE and "AS runtime" in DOCKERFILE
    assert "slim" in DOCKERFILE


def test_requirements_copied_before_source():
    assert DOCKERFILE.index("COPY requirements.txt") < DOCKERFILE.index("COPY --chown=agent:agent app/")


def test_non_root_user_and_healthcheck_and_port():
    assert "10001" in DOCKERFILE
    assert re.search(r"^USER agent", DOCKERFILE, re.M)
    assert "HEALTHCHECK" in DOCKERFILE and "/health" in DOCKERFILE
    assert "0.0.0.0" in DOCKERFILE and "${PORT:-8000}" in DOCKERFILE


def test_dockerignore_minimum():
    lines = {l.strip() for l in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()}
    assert {".env", ".git", ".venv", "__pycache__"} <= lines


def test_compose_has_agent_and_redis_via_service_name():
    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert re.search(r"^  agent:", text, re.M) and re.search(r"^  redis:", text, re.M)
    assert "redis://redis:6379/0" in text
    assert "localhost:6379" not in text


def _docker_ok():
    if not shutil.which("docker"):
        return False
    return subprocess.run(["docker", "info"], capture_output=True).returncode == 0


@pytest.mark.docker
@pytest.mark.skipif(not _docker_ok(), reason="Docker daemon không chạy")
def test_image_builds_small_and_runs_as_non_root():
    subprocess.run(["docker", "build", "-t", "day12-agent:prod", str(ROOT)], check=True, capture_output=True)
    size = int(subprocess.check_output(["docker", "image", "inspect", "day12-agent:prod", "--format", "{{.Size}}"]))
    assert size < 500 * 1024 * 1024
    uid = subprocess.check_output(["docker", "run", "--rm", "--entrypoint", "id", "day12-agent:prod", "-u"], text=True)
    assert uid.strip() == "10001"
