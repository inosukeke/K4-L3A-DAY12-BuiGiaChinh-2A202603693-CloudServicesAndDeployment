# Day 12 Lab - Mission Answers

Bùi Gia Chính - 2A202603693. Số liệu lấy từ lần chạy thật trên máy local (Docker Desktop 28.0.4, Windows 11); output đầy đủ ở [screenshots/local-docker-evidence.txt](screenshots/local-docker-evidence.txt).

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found

Đọc `01-localhost-vs-production/develop/app.py`:

1. API key và `DATABASE_URL` (kèm mật khẩu) viết thẳng trong code. Push lên GitHub là lộ ngay và không đổi được nếu không sửa code.
2. Config (`DEBUG`, `MAX_TOKENS`) cố định trong code, không đọc từ biến môi trường nên không đổi được giữa dev và production.
3. Dùng `print()` thay vì log có cấu trúc, và còn in cả API key ra log.
4. Không có endpoint `/health`, nên nền tảng không biết khi nào cần restart container.
5. `host="localhost"` và `port=8000` cố định. Trong container, `localhost` không nhận được kết nối từ ngoài; Railway/Render cấp cổng qua biến `PORT`.
6. `reload=True` là chế độ debug, không nên bật ở production.
7. Không xử lý SIGTERM, nên khi cloud dừng container thì request đang chạy bị cắt.
8. Không có xác thực: ai biết URL cũng gọi được và tiêu tiền LLM.

### Exercise 1.3: Comparison table

| Feature | Develop | Production | Why Important? |
|---------|---------|------------|----------------|
| Config | Hardcode trong code | Biến môi trường (12-Factor) | Cùng một image chạy được ở mọi môi trường, secret không nằm trong Git |
| Health check | Không có | `/health` (liveness) và `/ready` (readiness) | Platform biết khi nào restart, load balancer biết khi nào ngừng gửi traffic |
| Logging | `print()`, lộ secret | JSON một dòng mỗi sự kiện | Log aggregator parse được, không lộ secret |
| Shutdown | Bị cắt đột ngột | Graceful: bật cờ, hoàn tất request đang chạy | Không mất request khi deploy lại |
| Host/Port | `localhost:8000` | `0.0.0.0` và `PORT` từ env | Container và PaaS truy cập được |

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

Đọc `02-docker/develop/Dockerfile`:

1. Base image: `python:3.11` (bản đầy đủ, khoảng 1 GB).
2. Working directory: `/app`.
3. `COPY requirements.txt` trước mã nguồn để tận dụng layer cache: khi chỉ sửa code, Docker dùng lại layer `pip install` thay vì cài lại toàn bộ dependency.
4. `CMD` là lệnh mặc định và bị thay được khi chạy `docker run <image> <lệnh khác>`. `ENTRYPOINT` là chương trình cố định, đối số truyền vào được nối vào sau nó. Bài này dùng `CMD`.

### Exercise 2.3: Image size comparison

Đo bằng `docker image inspect`:

- Develop (`python:3.11`, một stage): 1150 MB (1.15 GB)
- Production (`python:3.11-slim`, multi-stage): 189 MB
- Difference: nhỏ hơn khoảng 84%

Image production nhỏ vì hai lý do. Base là `slim` nên không kèm bộ công cụ build. Multi-stage chỉ copy virtualenv đã cài sẵn từ stage `builder` sang stage `runtime`, còn pip cache và công cụ build ở lại stage builder.

### Exercise 2.4: Docker Compose stack

Stack của bài (file `docker-compose.yml`): `agent` (FastAPI) kết nối tới `redis` qua hostname `redis` trong mạng nội bộ của Compose (`redis://redis:6379/0`). Agent chỉ start sau khi Redis `healthy` (`depends_on` + `condition: service_healthy`). Khi scale, file `docker-compose.scale.yml` thêm Nginx ở cổng 8080, và Nginx phân phối request cho các container `agent` qua DNS nội bộ của Docker.

```
Client -> Nginx :8080 -> agent-1 / agent-2 / agent-3 -> Redis
```

Bài này cần hai service (agent, redis) nên tôi để Nginx trong file override riêng.

## Part 3: Cloud Deployment

### Exercise 3.1: Deployment

- URL: https://day12-agent-production-b2e0.up.railway.app (Railway, gồm service agent và Redis). Kết quả kiểm tra ở [DEPLOYMENT.md](DEPLOYMENT.md).
- Lỗi gặp khi deploy: `REDIS_URL` tham chiếu sai tên service (`day12-redis` thay vì `Redis`) nên thành chuỗi rỗng. `/health` vẫn 200 còn `/ready` trả 503, đúng như thiết kế tách liveness và readiness. Sửa tham chiếu rồi redeploy thì hết lỗi.
- Đã chuẩn bị sẵn `railway.toml` và `render.yaml`. Khác biệt chính: `railway.toml` chỉ mô tả cách build và deploy, còn Redis thêm bằng plugin trên dashboard. `render.yaml` là Blueprint mô tả cả hạ tầng (web service và Key Value) và tự nối `REDIS_URL`, tự sinh `AGENT_API_KEY`.
- Đã chạy thật bằng Docker Compose ở local, kết quả ở [screenshots/local-docker-evidence.txt](screenshots/local-docker-evidence.txt).

## Part 4: API Security

### Exercise 4.1-4.3: Test results

Chạy trên container thật (`http://localhost:8000`):

```
POST /ask không có key               -> 401
POST /ask sai key                    -> 401
POST /ask đúng key, X-User-Id: sv01  -> 200
12 request liên tiếp (limit 10/phút, đã dùng 2 lượt trước đó) -> 200 x8, rồi 429 x4 (kèm header Retry-After: 60)
```

Trả lời các câu hỏi của bài:

- API key được kiểm tra trong dependency `authenticate` ([app/auth.py](app/auth.py)), gắn vào `/ask` bằng `Depends`. Thiếu hoặc sai key đều trả 401. Bản mẫu `04-api-gateway/develop` trả 403 cho key sai; tôi gộp về 401 để không tiết lộ là key thiếu hay sai.
- So sánh key dùng `secrets.compare_digest` (constant-time) để tránh timing attack.
- Rotate key: đổi biến `AGENT_API_KEY` trên dashboard rồi restart. Không phải sửa code.
- JWT (Exercise 4.2): tôi chỉ đọc `04-api-gateway/production/auth.py`, không chạy và không dùng trong bài này. Flow là đăng nhập lấy token có `exp`, gửi qua `Authorization: Bearer`, server verify chữ ký nên không cần tra DB mỗi request.
- Rate limiting: thuật toán của bài là sliding window bằng Redis Sorted Set ([app/rate_limiter.py](app/rate_limiter.py)): xóa member cũ hơn 60 giây, đếm phần còn lại, kiểm tra giới hạn, thêm request mới với member duy nhất, đặt TTL. Limit là 10 request/phút cho mỗi `X-User-Id`, chỉnh bằng `RATE_LIMIT_PER_MINUTE`. Bản mẫu in-memory (`04-api-gateway/production/rate_limiter.py`) cho admin 100 request/phút, user 10 request/phút; bài của tôi chưa có phân quyền admin.

Hạn chế đã biết: `X-User-Id` do client tự gửi, nên ai có API key có thể đổi user id để né rate limit theo user. Bài lab chỉ có một API key dùng chung nên chưa giải quyết được; muốn chặt hơn thì gắn user id vào key (mỗi user một key) hoặc dùng JWT.

### Exercise 4.4: Cost guard implementation

([app/cost_guard.py](app/cost_guard.py))

- Mỗi user có ngân sách theo tháng (`MONTHLY_BUDGET_USD`, mặc định 10). Chi phí lưu trong Redis ở key `cost:<user>:<YYYY-MM>`, sang tháng mới thì key mới nên tự "reset"; key có TTL 35 ngày để tự dọn.
- Trước khi gọi LLM: `check_budget` đọc số đã tiêu, nếu đã đạt ngân sách thì trả 402 và LLM không được gọi (có test kiểm tra điều này).
- Sau khi LLM trả kết quả: `record_cost` cộng chi phí thật của request bằng `INCRBYFLOAT`. Chi phí ước tính từ số từ của câu hỏi và câu trả lời, giá theo mức gpt-4o-mini.
- Khác với lời giải mẫu trong CODE_LAB (kiểm tra và cộng cùng lúc bằng chi phí ước tính), tôi tách thành hai bước đúng thứ tự yêu cầu: kiểm tra trước, ghi nhận sau. Hệ quả: request cuối cùng có thể đẩy tổng vượt ngân sách một chút, vì lúc kiểm tra chưa biết chi phí của chính nó.
- Kiểm chứng trên container với `MONTHLY_BUDGET_USD=0.00003`: 200, 200, rồi 402.

## Part 5: Scaling & Reliability

### Exercise 5.1-5.5: Implementation notes

**5.1 Health và readiness** ([app/main.py](app/main.py))

| Tình trạng | `/health` | `/ready` |
|---|---|---|
| Process và Redis đều ổn | 200 | 200 |
| Redis dừng | 200 | 503 |
| Đang shutdown | 503 | 503 |

`/health` không gọi Redis vì nó chỉ trả lời "process còn sống không". Nếu `/health` phụ thuộc Redis thì Redis chết sẽ khiến nền tảng restart agent vô ích. Đã kiểm chứng: dừng Redis thì `/health` 200, `/ready` 503 và `/ask` 503; bật lại Redis thì `/ready` về 200.

**5.2 Graceful shutdown** ([app/lifecycle.py](app/lifecycle.py))

- Handler mới cho SIGTERM và SIGINT bật cờ `shutting_down` (để `/ready` và `/health` trả 503), sau đó gọi lại handler cũ nếu nó callable, để Uvicorn tiếp tục dừng an toàn.
- Việc đăng ký nằm trong `lifespan` của FastAPI, không phải lúc import module: Uvicorn cài handler của nó sau khi import app, nên đăng ký sớm hơn sẽ bị ghi đè và handler "cũ" mình lưu sẽ không phải của Uvicorn.
- Thử thật: gửi 12 request song song rồi SIGTERM ngay giữa chừng, cả 12 request đều trả 200 và container thoát với exit code 0 (log: `Shutting down` → `Application shutdown complete`).

**5.3 Stateless** ([app/store.py](app/store.py))

- Conversation history nằm trong Redis (`history:<user>`), không có dict toàn cục trong process. Mỗi lượt ghi bằng `RPUSH`, `LTRIM` giữ 20 message gần nhất, và `EXPIRE` 3600 giây để lịch sử cũ tự hết hạn (kiểm tra: `LLEN` luôn là 20, `TTL` khoảng 3597).
- Rate limit và cost cũng nằm trong Redis nên giới hạn áp dụng chung cho mọi instance.
- `ping()` bắt mọi exception và trả `False`, nên `/ready` không bao giờ văng lỗi 500 khi Redis chết.

**5.4 Load balancing**

Chạy `docker compose -f docker-compose.yml -f docker-compose.scale.yml up -d --scale agent=3`. Với cùng `X-User-Id: scale1`, 9 request liên tiếp đi qua 3 container khác nhau (trường `served_by`), và `history_messages` tăng đều 0, 2, 4, ... 16 dù đổi container. Sau khi `docker kill` một container, các request tiếp theo vẫn trả 200 và history vẫn còn (đã chạm giới hạn 20 message). Nginx dùng `proxy_next_upstream` để thử instance khác khi một instance lỗi.

Lưu ý quan sát được: Nginx chia request không đều giữa các instance (có lúc 5 request liên tiếp vào cùng một container) vì cách nó resolve DNS. Không ảnh hưởng tính đúng đắn vì state ở Redis.

**5.5 Test stateless**

Tôi không chạy `05-scaling-reliability/production/test_stateless.py` vì script đó dành cho stack riêng của thư mục 05. Thay vào đó tôi tự kiểm chứng bằng bài test ở mục 5.4 và các test tự động trong `tests/test_cp4.py` (39 test, tất cả đạt khi chạy `pytest tests/ -v`).
