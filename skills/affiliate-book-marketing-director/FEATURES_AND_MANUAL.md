# FEATURES_AND_MANUAL - Affiliate Book Marketing Director

## 1) Tổng quan hệ thống
- Mục tiêu: tự động vận hành Affiliate Sách đa page Facebook (+IG tùy điều kiện), gồm đăng bài, tạo ảnh, quét tương tác, và báo cáo.
- Nguồn dữ liệu: Google Sheets CSV (BOOKS_CSV_URL) với cột STT, ID Page, Ngày đăng, Giờ đăng, Tên sách, Ý chính, Link Aff, Loại bài.

## 2) Luồng đăng bài

### 2.1 Build queue
- Script: `scripts/run_morning_pipeline.py`
- Mode: `PIPELINE_MODE=build_queue`
- Chức năng:
  - đọc sheet
  - map mỗi dòng -> đúng `page_id`
  - tạo queue item có caption + image prompt + publish_at

### 2.2 Dispatch due
- Script: `scripts/run_morning_pipeline.py`
- Mode: `PIPELINE_MODE=dispatch_due`
- Chức năng:
  - duyệt queue đến hạn
  - render ảnh nền Cloudflare + overlay chữ Việt bằng Pillow
  - đăng lên Facebook
  - Affiliate: thêm comment link nếu có `affiliate_link` hợp lệ

## 3) Luồng ảnh
- Cloudflare AI render background theo visual metaphor prompt.
- Pillow chèn text tiếng Việt (Unicode-safe) với:
  - wrap text
  - dark overlay
  - drop shadow
- Nếu Cloudflare Images upload URL lỗi: fallback upload ảnh local trực tiếp lên FB.

## 4) Luồng Content
- Cấu trúc AIDA + trend-jacking.
- Bài dài chuẩn (mục tiêu 250-400+ từ), giữ định dạng xuống dòng `\n\n`.
- Không cắt cụt CTA/hashtags ở cuối bài.

## 5) Luồng tương tác số 5 (Comment Triage)
- Script: `scripts/run_comment_triage.py`
- Mục tiêu:
  - quét comment mới từ các bài gần nhất trên từng page
  - phân loại intent: `buy_intent` vs `casual`

### 5.1 Quy tắc xử lý (đã chuyển sang public-only)
- Buy intent:
  - KHÔNG dùng private reply/inbox
  - reply công khai trực tiếp dưới bài với link affiliate:
    - `Dạ sách đang có ưu đãi, bạn đặt mua chính hãng tại link này nhé: [Link Aff]`
- Casual:
  - reply cảm ơn thân thiện

### 5.2 Chạy DRY_RUN
- `DRY_RUN=1` chỉ mô phỏng + log hành vi dự kiến.

## 6) Tự động hóa cron (đang bật)
- 07:00 hằng ngày:
  - `cron-morning.sh` (build queue)
- Mỗi 15 phút:
  - `cron-triage.sh` (quét comment/triage)
- 21:30 Chủ Nhật:
  - `cron-weekly-report.sh`

Cron hiện tại:
- `0 7 * * * /root/.openclaw/workspace/skills/affiliate-book-marketing-director/scripts/cron-morning.sh`
- `*/15 * * * * /root/.openclaw/workspace/skills/affiliate-book-marketing-director/scripts/cron-triage.sh`
- `30 21 * * 0 /root/.openclaw/workspace/skills/affiliate-book-marketing-director/scripts/cron-weekly-report.sh`

## 7) Biến môi trường quan trọng
- `META_ACCESS_TOKEN`
- `CF_ACCOUNT_ID`
- `CF_API_TOKEN`
- `BOOKS_CSV_URL`
- `TEST_PAGE_ID` (tùy chọn)
- `DRY_RUN` (`1` test, `0` live)
- `PIPELINE_MODE` (`build_queue` / `dispatch_due`)
- `ENABLE_FRIDAY_SPECIAL` (`1` để bật minigame Thứ Sáu)

## 8) Log theo dõi
- `state/affiliate_marketing.log`
- `state/affiliate_marketing_error.log`
- `state/affiliate_publish_queue.json`
- `state/comment_triage_state.json`

Lưu ý: Triage hiện tại chạy theo chiến lược `public_reply_only` để tránh lỗi permission của Meta Messaging.
