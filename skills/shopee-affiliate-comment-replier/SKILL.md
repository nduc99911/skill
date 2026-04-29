---
name: shopee-affiliate-comment-replier
description: Auto-compose short friendly Vietnamese replies to customer comments by extracting real Shopee affiliate link(s) from original post content. Use when handling comments like xin link, hỏi giá, chấm, icon, khen, hoặc mua thế nào under product posts.
---

# Shopee Affiliate Comment Replier

Use this skill when the user wants customer-comment replies for Shopee affiliate posts.

## Inputs
- `post_content`: original post text/caption
- `customer_comment`: customer comment text

## Required behavior
1. Extract Shopee link from `post_content` only.
   - Accept domains like `shopee.vn`, `s.shopee.vn`, `shp.ee`, `shpe.ee`.
2. Infer intent from comment:
   - `ask_link`: xin link / chấm / . / ib
   - `ask_price`: hỏi giá / sale
   - `ask_attribute`: hỏi size, màu, chất liệu, ship, cod, đổi trả
   - `phone_number`: để lại số điện thoại công khai
   - `strong_buy`: chốt đơn mạnh như `chốt nha`, `lấy mình cái này`
   - `praise`: khen / thả icon
   - `generic`: còn lại
3. Output final reply text only (send-ready), max 3 sentences.
4. Keep architecture independent; do not rely on any other skill runtime.

## Hard rules
- Never invent link.
- If no Shopee link exists in `post_content`, output exactly:
  - `Dạ bạn đợi chút xíu, mình đang kiểm tra lại link sản phẩm và sẽ gửi bạn ngay nhé ạ! Cảm ơn bạn quan tâm.`
- Tone: friendly, natural, polite Vietnamese (`mình-bạn` or `shop-bạn`).
- Reply should start with greeting (e.g., `Dạ mình chào bạn ạ`, `Dạ shop chào bạn`, `Chào bạn nha`).
- For repeated comments of the same intent, prefer varied phrasings to avoid spammy repetition.
- For public phone numbers, gently steer users away from posting sensitive info in comments and direct them to Shopee link instead.

## Deterministic generation
Use these scripts for production:
- `scripts/page_selector.py` — pick Meta Page interactively and save `page_id` + `page_access_token`
- `scripts/reply_builder.py` — build customer reply text

Example:
```bash
python3 skills/shopee-affiliate-comment-replier/scripts/reply_builder.py \
  --post-content "... https://s.shopee.vn/abc ..." \
  --comment "cho mình xin link"
```

The reply script prints only final reply text.

Before wiring webhook/live replies, run page selection once:
```bash
python3 skills/shopee-affiliate-comment-replier/scripts/page_selector.py
```
This fetches `/me/accounts`, shows a numbered page menu, and saves the chosen Page into:
- `skills/shopee-affiliate-comment-replier/config/config.json`
