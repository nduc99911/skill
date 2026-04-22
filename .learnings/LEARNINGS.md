# Learnings

Corrections, insights, and knowledge gaps captured during development.

**Categories**: correction | insight | knowledge_gap | best_practice

---

## [LRN-20260422-001] correction

**Logged**: 2026-04-22T13:30:00+07:00
**Priority**: high
**Status**: pending
**Area**: config

### Summary
Enforce Vietnamese-only output and remove markdown/CTA artifacts across all Facebook pages.

### Details
User reported recurring issues: mixed English-Vietnamese text, asterisk formatting, and unnecessary template sections (CTA/chuyển đổi/gợi ý). Updated generation constraints globally in posting script so every page follows clean native Vietnamese style.

### Suggested Action
Keep hard constraints in generation prompt and periodically audit recent posts for violations.

### Metadata
- Source: user_feedback
- Related Files: scripts/thuc-thi-dang-bai.sh
- Tags: facebook, content-quality, language-control

---
