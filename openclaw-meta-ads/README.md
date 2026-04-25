# OpenClaw Meta Ads AI - MVP 1.0

Hệ thống OpenClaw Meta Ads AI là một bộ skill theo kiến trúc module, được thiết kế để hỗ trợ một người vận hành Meta Ads theo mô hình single-user.

Mục tiêu của MVP 1.0:
- đọc số liệu thật từ Meta Ads API
- phân tích hiệu suất theo rule rõ ràng
- gợi ý creative/copy mới một cách có cấu trúc
- tạo testing matrix để triển khai
- sinh draft campaign an toàn trước khi gọi Write API

Điểm cốt lõi của hệ thống là: đọc dữ liệu thật, tư duy như CMO, nhưng thực thi write cực kỳ thận trọng.

---

## 1. Kiến trúc tổng thể

Thư mục gốc:

```text
openclaw-meta-ads/
├── README.md
├── .gitignore
├── meta-ads-api-core/
├── meta-ads-insights-reporter/
├── meta-ads-optimizer/
├── meta-ads-copywriter/
├── meta-ads-creative-matrix/
├── meta-ads-campaign-drafter/
└── meta-ads-orchestrator/
```

---

## 2. Danh sách 6 skill và chức năng

### 1) meta-ads-api-core
Skill nền tảng giao tiếp với Meta Graph API.

Chức năng:
- xây dựng URL versioned theo `META_API_VERSION`
- gọi API cơ bản với token lấy từ env
- parse lỗi chi tiết từ Meta (`message`, `type`, `code`, `subcode`)
- hỗ trợ auto-pagination qua `paging.next`

Guardrail:
- không bao giờ log token
- write mặc định bị chặn hoặc paused/dry-run

### 2) meta-ads-insights-reporter
Skill đọc báo cáo hiệu suất quảng cáo.

Chức năng:
- gọi endpoint `/{META_AD_ACCOUNT_ID}/insights`
- lấy số liệu ở level campaign/adset/ad
- format về Markdown table
- parse các trường đặc thù như:
  - `actions` -> Purchases
  - `action_values` -> Revenue
  - `purchase_roas` -> ROAS
  - tính CPA

### 3) meta-ads-optimizer
AI Rule Engine để chẩn đoán campaign.

Chức năng:
- phân nhóm campaign theo hành động:
  - 🔴 TẮT NGAY
  - 🟢 SCALE
  - 🟡 THAY CREATIVE
  - 🔵 THEO DÕI
- tạo output Markdown dễ đọc cho người vận hành

### 4) meta-ads-copywriter
AI Copywriter tạo nội dung quảng cáo theo angle.

Chức năng:
- viết nhiều angle quảng cáo mới
- mỗi angle gồm:
  - Hook
  - Primary Text
  - Headline
  - CTA

Guardrail policy:
- không claim quá đà
- không nhắm vào personal attributes
- không before/after cực đoan

### 5) meta-ads-creative-matrix
Skill chuyển hóa angle thành bảng testing matrix.

Chức năng:
- dựng ma trận creative test
- gợi ý format:
  - Video UGC
  - Image
  - Carousel
- thêm visual concept và funnel stage

### 6) meta-ads-campaign-drafter
Skill draft campaign an toàn trước khi write API.

Chức năng:
- sinh Approval Packet cho user duyệt
- sinh payload JSON draft cho:
  - Campaign
  - Ad Set
  - Ads
- có Pre-flight Check để chặn payload lỗi

Guardrail tối thượng:
- mọi payload phải `status: PAUSED`
- MVP không được publish live trực tiếp
- luôn phải có Approval Packet trước khi nghĩ đến POST

---

## 3. Orchestrator: quy trình vận hành 5 bước

Skill điều phối: `meta-ads-orchestrator`

Workflow chuẩn:

### Bước 1: Pull Insights
- dùng `meta-ads-insights-reporter`
- lấy báo cáo 7 ngày / 30 ngày từ Meta Ads API

### Bước 2: Diagnose
- dùng `meta-ads-optimizer`
- xác định campaign nào nên tắt, scale, thay creative hoặc tiếp tục theo dõi

### Bước 3: Generate New Copy
- dùng `meta-ads-copywriter`
- tạo angle mới cho campaign bị creative fatigue hoặc cần test thêm

### Bước 4: Build Creative Matrix
- dùng `meta-ads-creative-matrix`
- chuyển angle thành bảng test có cấu trúc

### Bước 5: Draft Campaign Safely
- dùng `meta-ads-campaign-drafter`
- tạo approval packet
- sinh payload JSON draft
- chạy pre-flight checklist
- chỉ khi user duyệt mới được xem xét chuyển sang write API thật

---

## 4. Cấu hình biến môi trường (.env)

Tạo file `.env` ở môi trường chạy với các biến như sau:

```env
META_ACCESS_TOKEN=
META_AD_ACCOUNT_ID=
META_API_VERSION=v23.0
META_PAGE_ID=
```

Biến mở rộng tùy nhu cầu:

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

Giải thích:
- `META_ACCESS_TOKEN`: token dùng để đọc Meta Graph API
- `META_AD_ACCOUNT_ID`: ad account dạng `act_xxx`
- `META_API_VERSION`: version Graph API, mặc định `v23.0`
- `META_PAGE_ID`: page id để gắn creative draft
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`: nếu muốn tích hợp báo cáo Telegram

Lưu ý:
- không commit `.env` lên Git
- không log token vào file hoặc terminal

---

## 5. Guardrails bảo mật và an toàn

Đây là phần quan trọng nhất của hệ thống.

### A. Mặc định PAUSED
- mọi payload draft ở cấp Campaign / Ad Set / Ad đều phải có:

```json
"status": "PAUSED"
```

### B. Không publish live trong MVP
- `meta-ads-campaign-drafter` chỉ tạo draft
- không được gọi POST write API thật nếu chưa có lớp duyệt riêng

### C. Pre-flight Checklist bắt buộc
Trước mọi ý định write, hệ thống phải kiểm tra:
- Ad có media asset chưa (`image_hash` hoặc `video_id`)
- Ad có destination URL chưa
- URL có UTM tracking hay chưa
- daily budget có đủ ngưỡng tối thiểu không
- tất cả status có phải `PAUSED` không

Nếu thiếu trường bắt buộc:
- hệ thống phải trả:
  - `🚫 BLOCKED: Payload thiếu trường bắt buộc. Hệ thống từ chối gọi API.`

### D. Token Hygiene
- không log hoặc in raw token
- mọi lỗi chỉ in metadata lỗi từ Meta, không lộ secret

---

## 6. Cách dùng nhanh

### Test Insights Reporter
```bash
python3 meta-ads-insights-reporter/insights_reporter.py
```

### Test Optimizer
```bash
python3 meta-ads-optimizer/optimizer.py
```

### Test Creative Loop
```bash
python3 meta-ads-creative-matrix/matrix_builder.py
```

### Test Draft Campaign + Pre-flight
```bash
python3 meta-ads-campaign-drafter/campaign_drafter.py
```

### Chạy toàn bộ Orchestrator
```bash
python3 meta-ads-orchestrator/pipeline_runner.py
```

---

## 7. Trạng thái hiện tại của MVP

MVP 1.0 đã hoàn thiện đủ 6 skill:
- đọc số liệu
- phân tích rule-based
- sáng tạo copy
- dựng matrix
- draft campaign an toàn
- orchestration end-to-end

Điểm dừng an toàn hiện tại:
- hệ thống dừng ở Approval Packet + Payload Draft
- chưa tự động write live campaign

Đây là chủ đích thiết kế để đảm bảo an toàn tuyệt đối trước khi mở rộng sang phase write thật.
