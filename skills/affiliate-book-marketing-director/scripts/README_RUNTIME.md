Runtime quickstart (manual):

1) Export session env vars (do not hardcode in files):
- META_ACCESS_TOKEN
- FB_PAGE_ID
- IG_BUSINESS_ID
- CF_ACCOUNT_ID
- CF_API_TOKEN
- BOOKS_CSV_PATH (optional)

2) Morning pipeline:
python3 skills/affiliate-book-marketing-director/scripts/run_morning_pipeline.py

3) Continuous triage (run by cron every 10-15 min):
python3 skills/affiliate-book-marketing-director/scripts/run_comment_triage.py

4) Weekly report (Sunday night):
python3 skills/affiliate-book-marketing-director/scripts/run_weekly_report.py

Notes:
- Tokens are runtime-only.
- All errors logged in state/affiliate_marketing_error.log
