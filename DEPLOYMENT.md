# Deployment Information

- **Họ tên:** Bùi Gia Chính
- **Mã học viên:** 2A202603693
- **Repository:** `K4-L3A-DAY12-BuiGiaChinh-2A202603693-CloudServicesAndDeployment`

## Trạng thái triển khai

| Hạng mục | Trạng thái |
|---|---|
| Chạy thật bằng Docker Compose trên máy local (agent + redis) | Đã chạy và kiểm tra, bằng chứng ở [screenshots/local-docker-evidence.txt](screenshots/local-docker-evidence.txt) |
| Scale 3 instance sau Nginx | Đã chạy và kiểm tra |
| Public URL HTTPS trên Railway | Đã triển khai và kiểm tra, bằng chứng ở [screenshots/cloud-railway-evidence.txt](screenshots/cloud-railway-evidence.txt) |

## Public URL

```
https://day12-agent-production-b2e0.up.railway.app
```

## Nền tảng

Railway (region US West, 1 replica), project gồm 2 service:

- `day12-agent`: build từ [Dockerfile](Dockerfile) theo [railway.toml](railway.toml), health check `/health`, tự deploy lại khi push lên `main`.
- `Redis`: Redis của Railway, có volume `redis-volume`.

[render.yaml](render.yaml) để sẵn cho Render nhưng chưa dùng.

## Biến môi trường cần cấu hình trên dashboard

Chỉ ghi tên biến; giá trị secret nhập trực tiếp trên dashboard, không nằm trong repo.

| Biến | Ghi chú |
|---|---|
| `AGENT_API_KEY` | Secret. Thiếu biến này app dừng ngay khi khởi động |
| `REDIS_URL` | Railway: `${{Redis.REDIS_URL}}` (tham chiếu tới service `Redis`; tên service sai thì biến thành chuỗi rỗng và `/ready` trả 503); Render: lấy từ Key Value (đã khai báo trong `render.yaml`) |
| `RATE_LIMIT_PER_MINUTE` | Mặc định 10 |
| `MONTHLY_BUDGET_USD` | Mặc định 10 |
| `LOG_LEVEL` | `info` |

Không tự đặt `PORT`: nền tảng cấp sẵn và container đọc `${PORT:-8000}`.

## Các bước triển khai

Railway:
1. Đẩy repo lên GitHub (public). New Project → Deploy from GitHub repo.
2. Thêm plugin Redis, sau đó đặt các biến ở bảng trên trong tab Variables.
3. Settings → Networking → Generate Domain.

Render:
1. Đẩy repo lên GitHub (public). New → Blueprint → chọn repo, Render đọc `render.yaml`.
2. Kiểm tra các biến ở bảng trên trong tab Environment, rồi Deploy.

## Kết quả kiểm tra trên public URL (Railway, 2026-09-28)

| Lệnh | Kết quả |
|---|---|
| `GET /health` | 200 `{"status":"ok",...}` |
| `GET /ready` | 200 `{"ready":true,"redis":true}` |
| `POST /ask` không có key | 401 |
| `POST /ask` sai key | 401 |
| `POST /ask` đúng key, `X-User-Id: cloud-sv01`, hai lượt | 200, `history_messages` tăng 0 → 2 |
| 12 request liên tiếp, `X-User-Id: cloud-rl`, giới hạn 10/phút | 10 lần 200 rồi 2 lần 429 |

Sự cố gặp khi deploy: `REDIS_URL` ban đầu tham chiếu `${{day12-redis.DATABASE_URL}}`, nhưng service Redis trên Railway tên là `Redis`, nên biến này thành chuỗi rỗng. `/health` vẫn 200 (liveness không phụ thuộc Redis), còn `/ready` trả 503. Sửa thành `${{Redis.REDIS_URL}}` rồi redeploy thì `/ready` về 200.

## Kết quả kiểm tra (chạy thật bằng Docker Compose ở local, `http://localhost:8000`)

| Lệnh | Kết quả |
|---|---|
| `GET /health` | 200 `{"status":"ok",...}` |
| `GET /ready` | 200 `{"ready":true,"redis":true}` |
| `POST /ask` không có key | 401 |
| `POST /ask` sai key | 401 |
| `POST /ask` đúng key, `X-User-Id: evidence1` | 200, `history_messages` tăng 0 → 2 giữa hai lượt |
| 12 request liên tiếp, giới hạn 10/phút | 8 lần 200 rồi 4 lần 429 (2 lượt đã dùng trước đó) |
| `MONTHLY_BUDGET_USD=0.00003`, gọi liên tiếp | 200, 200, rồi 402 |
| Dừng Redis | `/health` 200, `/ready` 503, `/ask` 503; bật lại Redis thì `/ready` về 200 |
| SIGTERM khi 12 request đang chạy | Cả 12 request trả 200, container thoát exit code 0 |
| `--scale agent=3` sau Nginx (cổng 8080) | Cùng `X-User-Id` đi qua 3 container khác nhau, history vẫn liên tục; kill 1 container, service vẫn trả 200 |

Kích thước image `day12-agent:prod`: 189 MB, chạy bằng UID 10001.

## Lệnh kiểm tra sau khi có public URL

```bash
URL=https://day12-agent-production-b2e0.up.railway.app

curl -i "$URL/health"    # mong đợi 200
curl -i "$URL/ready"     # mong đợi 200 và redis=true
curl -i -X POST "$URL/ask" -H "Content-Type: application/json" \
  -d '{"question":"Hello"}'                                  # mong đợi 401 khi thiếu key
curl -i -X POST "$URL/ask" -H "Content-Type: application/json" \
  -H "X-API-Key: $AGENT_API_KEY" -H "X-User-Id: sv01" \
  -d '{"question":"Docker la gi?"}'                           # mong đợi 200
```

## Ảnh minh chứng

- [screenshots/dashboard.png](screenshots/dashboard.png): Railway dashboard, 2 service `day12-agent` và `Redis` đều Online.
- [screenshots/running.png](screenshots/running.png): trình duyệt mở `/health` trên public URL.
- [screenshots/test.png](screenshots/test.png): kết quả `curl` trên public URL (bảng ở trên).
- [screenshots/cloud-railway-evidence.txt](screenshots/cloud-railway-evidence.txt): output dạng text của các lệnh trên public URL, API key đã che.
- [screenshots/local-docker-evidence.txt](screenshots/local-docker-evidence.txt): output thật của các lệnh chạy local (dạng text).
