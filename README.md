# Affiliate Book Marketing Director

Giám đốc Marketing AI cho hệ sinh thái OpenClaw, tối ưu cho mô hình bán sách affiliate đa fanpage Facebook và có thể mở rộng sang Instagram.

Hệ thống này gói trọn 3 lớp vận hành chính:
- Đăng bài tự động theo lịch từ Google Sheets CSV
- Tạo ảnh marketing bằng Cloudflare AI + Pillow overlay tiếng Việt
- Triage comment tự động với phân loại mua hàng / hỏi đáp / tiêu cực-spam

Mục tiêu là giúp một đội vận hành nhỏ hoặc một cá nhân có thể chạy nhiều fanpage affiliate sách với quy trình an toàn, có log, có cron, và dễ import sang môi trường OpenClaw mới.

## 1. Cài đặt / Import Skill

### Cách 1: Clone repository vào workspace OpenClaw
```bash
git clone https://github.com/nduc99911/skill.git
cd skill
```

### Cách 2: Copy riêng skill vào OpenClaw workspace
Đưa thư mục sau vào workspace của OpenClaw:

```text
skills/affiliate-book-marketing-director/
```

Tối thiểu cần các file:
- `skills/affiliate-book-marketing-director/SKILL.md`
- `skills/affiliate-book-marketing-director/FEATURES_AND_MANUAL.md`
- `skills/affiliate-book-marketing-director/scripts/`

Nếu muốn chạy đầy đủ pipeline, nên copy thêm các thư mục runtime liên quan:
- `data/`
- `config/` (chỉ giữ file mẫu, không commit secret thật)

## 2. Cấu trúc chính của skill

```text
skills/affiliate-book-marketing-director/
├── SKILL.md
├── FEATURES_AND_MANUAL.md
└── scripts/
    ├── config.py
    ├── logger.py
    ├── meta_api.py
    ├── cloudflare_api.py
    ├── books_source.py
    ├── trend_scanner.py
    ├── content_engine.py
    ├── run_morning_pipeline.py
    ├── run_comment_triage.py
    ├── run_weekly_report.py
    ├── cron-morning.sh
    ├── cron-triage.sh
    └── cron-weekly-report.sh
```

## 3. Cấu hình biến môi trường

Tạo file `.env.example` hoặc cấu hình trực tiếp trong môi trường chạy với các biến sau:

```env
# Meta / Facebook
META_ACCESS_TOKEN=
FB_PAGE_ID=
TEST_PAGE_ID=

# Cloudflare
CF_ACCOUNT_ID=
CF_API_TOKEN=

# Data source
BOOKS_CSV_URL=

# Runtime safety
DRY_RUN=1
PIPELINE_MODE=build_queue
ENABLE_FRIDAY_SPECIAL=0

# Optional LLM for dynamic comment reply
OPENAI_API_KEY=
```

### Ý nghĩa các biến
- `META_ACCESS_TOKEN`: user token dùng để gọi `/me/accounts` và lấy page token
- `FB_PAGE_ID`: page mặc định nếu muốn chạy cố định 1 page
- `TEST_PAGE_ID`: page test để nghiệm thu an toàn
- `CF_ACCOUNT_ID`: Cloudflare account id cho image generation
- `CF_API_TOKEN`: token gọi Workers AI / Cloudflare API
- `BOOKS_CSV_URL`: link publish CSV từ Google Sheets
- `DRY_RUN`: `1` để mô phỏng, `0` để chạy thật
- `PIPELINE_MODE`: `build_queue` hoặc `dispatch_due`
- `ENABLE_FRIDAY_SPECIAL`: bật minigame thứ Sáu nếu cần
- `OPENAI_API_KEY`: tùy chọn, dùng cho dynamic reply nâng cao ở phần comment triage

## 4. Kiến trúc hệ thống

### A. Luồng đăng bài
File chính:
- `scripts/run_morning_pipeline.py`

Nhiệm vụ:
- đọc dữ liệu từ Google Sheets CSV
- route từng dòng theo `ID Page`
- sinh caption theo phong cách AIDA
- build queue theo `Ngày đăng` + `Giờ đăng`
- dispatch bài đến hạn lên Facebook

An toàn vận hành:
- `DRY_RUN=1` mặc định
- hỗ trợ `TEST_PAGE_ID`
- có queue riêng để tránh đăng sai hàng loạt

### B. Luồng tạo ảnh
Các file chính:
- `scripts/cloudflare_api.py`
- `scripts/content_engine.py`

Kiến trúc:
- Cloudflare AI chỉ render background
- Pillow overlay text tiếng Việt lên ảnh
- fallback upload file trực tiếp lên Facebook nếu không có public image URL ổn định

Ưu điểm:
- kiểm soát typography tốt hơn
- tránh lỗi AI render chữ tiếng Việt sai
- phù hợp ảnh quote / visual metaphor cho page sách

### C. Luồng triage comment
File chính:
- `scripts/run_comment_triage.py`

Logic hiện tại:
- `buy_intent`:
  - reply trực tiếp vào comment khách bằng `POST /{comment_id}/comments`
  - thả link affiliate công khai
- `casual`:
  - sinh reply ngắn 1-2 câu theo ngữ cảnh
  - ưu tiên LLM nếu có `OPENAI_API_KEY`
  - fallback heuristic nếu không có key
- `negative_or_spam`:
  - bỏ qua hoàn toàn

Điểm quan trọng:
- triage hiện dùng **threaded reply** đúng luồng, không comment rời ra ngoài bài post

## 5. Cron gợi ý

Ví dụ cron đang dùng:

```cron
0 7 * * * /root/.openclaw/workspace/skills/affiliate-book-marketing-director/scripts/cron-morning.sh
*/15 * * * * /root/.openclaw/workspace/skills/affiliate-book-marketing-director/scripts/cron-triage.sh
30 21 * * 0 /root/.openclaw/workspace/skills/affiliate-book-marketing-director/scripts/cron-weekly-report.sh
```

## 6. Gợi ý vận hành an toàn
- Luôn test bằng `TEST_PAGE_ID` trước khi bỏ giới hạn
- Không commit token thật vào Git
- Không commit thư mục `state/`
- Khi đổi token Meta, nên test lại:
  - `/me/accounts`
  - đọc comment
  - threaded reply comment

## 7. Logs và trạng thái runtime
Các file sau chỉ dùng runtime, không nên commit:
- `state/affiliate_marketing.log`
- `state/affiliate_marketing_error.log`
- `state/affiliate_publish_queue.json`
- `state/comment_triage_state.json`
- các history / queue / report runtime khác

## 8. Mục tiêu sử dụng
Skill này phù hợp nếu bạn muốn:
- vận hành nhiều page affiliate sách với một user token Meta
- kiểm soát caption dài, tự nhiên, có chiến lược bán hàng
- tự động hóa comment theo hướng giống người thật
- dễ mang sang môi trường OpenClaw mới để tái sử dụng
