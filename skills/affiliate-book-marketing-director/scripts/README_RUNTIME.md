Runtime quickstart (manual):

1) Export session env vars (do not hardcode in files):
- META_ACCESS_TOKEN (user token)
- CF_ACCOUNT_ID
- CF_API_TOKEN
- BOOKS_CSV_PATH (optional, default: data/books_today.sample.csv)
- PAGE_IG_MAP_PATH (optional mapping page_id -> ig_business_id)
- DRY_RUN=1 (recommended for testing)

Lưu ý: hệ thống sẽ tự gọi /me/accounts và loop qua toàn bộ page lấy được từ token.
FB_PAGE_ID chỉ là tùy chọn để filter 1 page khi debug.

2) Morning pipeline:
python3 skills/affiliate-book-marketing-director/scripts/run_morning_pipeline.py

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

Notes:
- Tokens are runtime-only.
- All errors logged in state/affiliate_marketing_error.log
