Runtime quickstart (manual):

1) Export session env vars (do not hardcode in files):
- META_ACCESS_TOKEN (user token)
- CF_ACCOUNT_ID
- CF_API_TOKEN
- DRY_RUN=1 (default an toàn; đổi 0 khi live thật)
- BOOKS_CSV_URL (Google Sheets Publish-to-web CSV URL) **ưu tiên cao nhất**
- BOOKS_CSV_PATH (fallback local CSV, default: data/books_today.sample.csv)
- TEST_PAGE_ID (nếu set thì chỉ chạy đúng 1 page này để nghiệm thu)
- PAGE_IG_MAP_PATH (optional mapping page_id -> ig_business_id)

Lưu ý: hệ thống tự gọi /me/accounts và loop qua toàn bộ page lấy được từ token.
Ưu tiên filter page: TEST_PAGE_ID > FB_PAGE_ID > tất cả pages.

2) Morning pipeline:
python3 skills/affiliate-book-marketing-director/scripts/run_morning_pipeline.py

Luồng tạo ảnh production hiện tại (đã nghiệm thu):
- Cloudflare AI render background theo visual metaphor prompt (4 bước: metaphor + setting + style modifiers + negative prompt)
- Pillow render text tiếng Việt lên ảnh (Unicode-safe)
- Có dark overlay + drop shadow + text wrap để tăng readability
- Nếu Cloudflare Images upload fail, Facebook sẽ fallback sang upload file local trực tiếp
- Trạng thái: approved for production rollout

3) Continuous triage (run by cron every 10-15 min):
python3 skills/affiliate-book-marketing-director/scripts/run_comment_triage.py

4) Weekly report (Sunday night):
python3 skills/affiliate-book-marketing-director/scripts/run_weekly_report.py

Cách đổi sang Long-lived token (để tránh chết sau ~2 giờ):
1. Vào Graph API Explorer, tạo short-lived User token với quyền cần thiết.
2. Dùng endpoint exchange token:
   GET https://graph.facebook.com/v19.0/oauth/access_token
   ?grant_type=fb_exchange_token
   &client_id={APP_ID}
   &client_secret={APP_SECRET}
   &fb_exchange_token={SHORT_LIVED_TOKEN}
3. Lấy access_token trong response -> export lại vào META_ACCESS_TOKEN.
4. Verify hạn token bằng Access Token Debugger.
5. Khi token đổi, chạy lại session env trước khi chạy cron/script.

Cron đề xuất:
- 00 07 * * * .../cron-morning.sh
- */15 * * * * .../cron-triage.sh
- 30 21 * * 0 .../cron-weekly-report.sh

Checklist On-Air (live thật):
1. BOOKS_CSV_URL: link CSV từ Google Sheets Publish to web.
2. META_ACCESS_TOKEN: long-lived token (~60 ngày).
3. TEST_PAGE_ID: ID page thử nghiệm trước.
4. CF_ACCOUNT_ID + CF_API_TOKEN: để render ảnh.

Notes:
- Tokens are runtime-only.
- All errors logged in state/affiliate_marketing_error.log
- Font tiếng Việt được tự tải về `assets/fonts/` khi cần; nếu tải font lỗi, hệ thống fallback font mặc định thay vì crash.
