# Day 12 — Deployment: Đưa Agent Lên Cloud

> **AICB-P1 · VinUniversity 2026**  
> Repository thực hành đi kèm bài giảng Day 12.  
> Mỗi phần có ví dụ **cơ bản** (hiểu concept) và **chuyên sâu** (production-ready).

---

## Bài làm: chạy nhanh (Bùi Gia Chính - 2A202603693)

Agent production-ready ở root repo: `app/` (config, logging JSON, auth, rate limit, cost guard, Redis store, lifecycle), `Dockerfile`, `docker-compose.yml`.

```bash
# 1. Tạo .env (xem mẫu ở cuối mục này), điền AGENT_API_KEY:
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 2. Chạy cả stack (agent + redis)
docker compose up -d --build
curl http://localhost:8000/health      # 200
curl http://localhost:8000/ready       # 200, redis=true

# 3. Gọi agent
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" \
  -H "X-API-Key: <AGENT_API_KEY>" -H "X-User-Id: sv01" -d '{"question":"Docker la gi?"}'

# 4. Scale 3 instance sau Nginx (cổng 8080)
docker compose -f docker-compose.yml -f docker-compose.scale.yml up -d --scale agent=3

# 5. Test (offline, dùng fakeredis) và kiểm tra production-ready
pip install -r requirements-dev.txt
pytest tests/ -v -m "not docker"
pytest tests/ -v            # thêm test build image (cần Docker)
python check_production_ready.py
```

Mẫu `.env` (không commit): `AGENT_API_KEY`, `PORT=8000`, `REDIS_URL=redis://localhost:6379/0` (chạy ngoài Docker; `fake://` nếu chưa có Redis), `LOG_LEVEL=info`, `RATE_LIMIT_PER_MINUTE=10`, `MONTHLY_BUDGET_USD=10.0`.

Tài liệu nộp bài: [MISSION_ANSWERS.md](MISSION_ANSWERS.md), [DEPLOYMENT.md](DEPLOYMENT.md), thư mục [screenshots/](screenshots/).

---

## Cấu Trúc Project

```
day12_ha-tang-cloud_va_deployment/
├── 01-localhost-vs-production/     # Section 1: Dev ≠ Production
│   ├── develop/                      #   Agent "đúng kiểu localhost"
│   └── production/                   #   12-Factor compliant agent
│
├── 02-docker/                      # Section 2: Containerization
│   ├── develop/                      #   Dockerfile đơn giản
│   └── production/                   #   Multi-stage + Docker Compose stack
│
├── 03-cloud-deployment/            # Section 3: Cloud Options
│   ├── railway/                    #   Deploy Railway (< 5 phút)
│   ├── render/                     #   Deploy Render + render.yaml
│   └── production-cloud-run/         #   GCP Cloud Run + CI/CD
│
├── 04-api-gateway/                 # Section 4: Security
│   ├── develop/                      #   API Key authentication
│   └── production/                   #   JWT + Rate Limiting + Cost Guard
│
├── 05-scaling-reliability/         # Section 5: Scale & Reliability
│   ├── develop/                      #   Health check + graceful shutdown
│   └── production/                   #   Stateless + Redis + Nginx LB
│
├── 06-lab-complete/                # Lab 12: Production-ready agent
│   └── (full project kết hợp tất cả)
│
├── Dockerfile_examples/            # Ví dụ Dockerfile (Go) + thứ tự layers
│   ├── Dockerfile                    #   Single-stage, COPY . . (chưa tối ưu)
│   ├── Dockerfile.deps-first         #   Dependencies trước, source sau (tối ưu)
│   └── Dockerfile.source-first       #   Source trước, dependencies sau (không tối ưu)
│
└── utils/                          # Mock LLM dùng chung (không cần API key)
```

---

## 🚀 Bắt Đầu Nhanh

**Muốn thử ngay?** → [QUICK_START.md](QUICK_START.md) (5 phút)

**Muốn học kỹ?** → [CODE_LAB.md](CODE_LAB.md) (3-4 giờ)

## Cách Học

| Bước | Làm gì |
|------|--------|
| 0 | **[Khuyến nghị]** Đọc [QUICK_START.md](QUICK_START.md) để thử nhanh |
| 1 | Đọc [CODE_LAB.md](CODE_LAB.md) để hiểu chi tiết |
| 2 | Chạy ví dụ **basic** trước — hiểu concept |
| 3 | So sánh với ví dụ **advanced** — thấy sự khác biệt |
| 4 | Tự làm Lab 06 từ đầu trước khi xem solution |
| 5 | Tham khảo [QUICK_REFERENCE.md](QUICK_REFERENCE.md) khi cần |
| 6 | Xem [TROUBLESHOOTING.md](TROUBLESHOOTING.md) khi gặp lỗi |

---

## Yêu Cầu

```bash
python 3.11+
docker & docker compose
```

Mỗi folder có `requirements.txt` riêng. Không cần API key thật — các ví dụ dùng **mock LLM** để chạy offline.

---

## Sections

| # | Folder | Concept chính |
|---|--------|--------------|
| 1 | `01-localhost-vs-production` | Dev/prod gap, 12-factor, secrets |
| 2 | `02-docker` | Dockerfile, multi-stage, docker-compose |
| 3 | `03-cloud-deployment` | Railway, Render, Cloud Run |
| 4 | `04-api-gateway` | Auth, rate limiting, cost protection |
| 5 | `05-scaling-reliability` | Health check, stateless, rolling deploy |
| 6 | `06-lab-complete` | **Full production agent** |

---

## 📚 Lab Materials

Chúng tôi đã chuẩn bị đầy đủ tài liệu hướng dẫn:

### Cho Sinh Viên

| Tài liệu | Mô tả | Thời gian |
|----------|-------|-----------|
| **[CODE_LAB.md](CODE_LAB.md)** | Hướng dẫn lab chi tiết từng bước | 3-4 giờ |
| **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** | Cheat sheet các lệnh và patterns | Tra cứu |
| **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** | Giải quyết lỗi thường gặp | Khi cần |

### Cho Giảng Viên

| Tài liệu | Mô tả |
|----------|-------|
| **[INSTRUCTOR_GUIDE.md](INSTRUCTOR_GUIDE.md)** | Hướng dẫn chấm điểm và đánh giá |

### Cách Sử Dụng

1. **Trước lab:** Đọc [CODE_LAB.md](CODE_LAB.md) để hiểu tổng quan
2. **Trong lab:** Làm theo từng Part, tham khảo [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
3. **Gặp lỗi:** Xem [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
4. **Sau lab:** Nộp Part 6 Final Project để chấm điểm
