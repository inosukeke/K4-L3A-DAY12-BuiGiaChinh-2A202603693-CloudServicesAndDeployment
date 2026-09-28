# Deployment Information

- **Họ tên:** Bùi Gia Chính
- **Mã học viên:** 2A202603693
- **Repository:** `K4-L3A-DAY12-BuiGiaChinh-2A202603693-CloudServicesAndDeployment`

## Trạng thái triển khai

| Hạng mục | Trạng thái |
|---|---|
| Chạy thật bằng Docker Compose trên máy local (agent + redis) | Đã chạy và kiểm tra, bằng chứng ở [screenshots/local-docker-evidence.txt](screenshots/local-docker-evidence.txt) |
| Scale 3 instance sau Nginx | Đã chạy và kiểm tra |
| Public URL HTTPS trên Railway / Render | **Chưa triển khai.** Cần đăng nhập tài khoản cloud; xem mục "Các bước triển khai" bên dưới |

Khi chưa có URL công khai, bài nộp dùng phương án local fallback (`LOCAL_FALLBACK=true`, CP5 tối đa 9/15 điểm). Khi đã deploy xong, điền URL và kết quả thật vào mục "Public URL" rồi bỏ dòng này.

## Public URL

```
(điền sau khi deploy) https://<domain-cua-ban>
```

## Nền tảng

Cấu hình sẵn cho cả hai nền tảng, chọn một:

- Railway: [railway.toml](railway.toml), build từ Dockerfile, health check `/health`.
- Render: [render.yaml](render.yaml), Blueprint gồm web service (Docker) và Key Value (Redis), `AGENT_API_KEY` do Render tự sinh.

## Biến môi trường cần cấu hình trên dashboard

Chỉ ghi tên biến; giá trị secret nhập trực tiếp trên dashboard, không nằm trong repo.

| Biến | Ghi chú |
|---|---|
| `AGENT_API_KEY` | Secret. Thiếu biến này app dừng ngay khi khởi động |
| `REDIS_URL` | Railway: `${{Redis.REDIS_URL}}`; Render: lấy từ Key Value (đã khai báo trong `render.yaml`) |
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
URL=https://<domain-cua-ban>

curl -i "$URL/health"    # mong đợi 200
curl -i "$URL/ready"     # mong đợi 200 và redis=true
curl -i -X POST "$URL/ask" -H "Content-Type: application/json" \
  -d '{"question":"Hello"}'                                  # mong đợi 401 khi thiếu key
curl -i -X POST "$URL/ask" -H "Content-Type: application/json" \
  -H "X-API-Key: <AGENT_API_KEY>" -H "X-User-Id: sv01" \
  -d '{"question":"Docker la gi?"}'                           # mong đợi 200
```

## Ảnh minh chứng

- [screenshots/local-docker-evidence.txt](screenshots/local-docker-evidence.txt): output thật của các lệnh ở bảng trên (dạng text).
- Ảnh chụp màn hình dashboard cloud và kết quả `curl` trên URL công khai: bổ sung vào `screenshots/` sau khi deploy.
