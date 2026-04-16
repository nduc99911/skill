---
name: book-affiliate-fb
description: Create Facebook book-post packages in two modes, AFF and VIRAL, from a book title or URL. AFF mode performs quick web research, writes a Vietnamese value-first affiliate post, prepares a first comment with affiliate-link placeholder, and provides or generates visuals for posting across one or more Facebook pages. VIRAL mode writes high-engagement non-sales book posts designed to earn comments, saves, and shares through quotes, listicles, or storytelling. Use when the user wants repeatable Facebook book content, affiliate posts, viral engagement posts, page-ready social copy, AI image prompts, optional image generation, or structured posting payloads for multiple pages.
---

# Book Affiliate FB

Create complete Facebook-ready book content packages for two distinct goals.

## Modes

### Mode 1: AFF
Use for affiliate-selling posts.

Goal:
- teach first
- recommend softly
- move the click into the first comment

Required characteristics:
- value-first body
- no affiliate link in the main post
- short first comment with link placeholder or supplied link
- optional AI image generation and Facebook posting payload

### Mode 2: VIRAL
Use for high-engagement, non-sales posts.

Goal:
- create emotional resonance
- increase comments, saves, and shares
- avoid overt selling

Required characteristics:
- no affiliate link in the main post
- no selling language
- end with either an open-ended question or a memorable save/share line
- choose the most suitable format automatically

Supported VIRAL formats:
- **Format A, Quote + reflection:** one strong quote or paraphrased line from the book plus a first-person reflection
- **Format B, Listicle:** examples like “3 ideas that changed how I see…”, “Top 5 lessons…”, “Don’t read X before you know…”
- **Format C, Storytelling:** a relatable struggle or failure arc, then the shift inspired by the book

## Input shorthand

Support concise user inputs when possible:

- `AFF;Tên sách;link aff;page 1`
- `VIRAL;Tên sách;page 1`
- `Tên sách;link aff;page 1` → default to AFF when an affiliate link is present
- `Tên sách;page 1` → ask or infer AFF vs VIRAL from context

## AFF workflow

1. Identify the book from the title or URL.
2. Research the book enough to extract practical lessons, pain points, and positioning.
3. Write a Vietnamese Facebook post that teaches first and sells softly.
4. Write a short first comment containing the exact placeholder `[CHÈN LINK AFFILIATE CỦA BẠN VÀO ĐÂY]` when no final link is supplied.
5. Provide visuals in two forms:
   - a detailed English image prompt
   - a high-quality cover-image URL when available
6. If the user wants the image created now, generate it.
7. If the user has a Facebook posting system or tokens, prepare or execute the posting flow.

## VIRAL workflow

1. Identify and research the book.
2. Choose the best format among Quote + reflection, Listicle, or Storytelling.
3. Write a Vietnamese post optimized for emotional connection and mobile readability.
4. Avoid any direct sales language.
5. End with either:
   - a question that invites comments
   - or a closing line that encourages saving/sharing naturally
6. Optionally provide or generate a thematic image, but do not force it if text alone is stronger.

## AFF output contract

Unless the user requests another format, return these sections in order:

### BƯỚC 1: THU THẬP THÔNG TIN
- Give a short summary of the book.
- Extract 3 high-value lessons, or 3 concrete problems the book helps solve.
- Keep it practical and Facebook-audience friendly.

### BƯỚC 2: VIẾT CONTENT BÀI ĐĂNG
Write in Vietnamese with these rules:
- Start with a pain-point hook or intriguing truth.
- Do not sell in the opening lines.
- Use short paragraphs, bullets, whitespace, and light emoji.
- Share 2 to 3 actionable lessons.
- End with a soft CTA that points readers to the first comment.
- Do not place any affiliate link in the main post.
- Add 4 to 6 relevant hashtags.

### BƯỚC 3: BÌNH LUẬN ĐẦU TIÊN
- Write one short, natural first comment.
- Include the exact placeholder: `[CHÈN LINK AFFILIATE CỦA BẠN VÀO ĐÂY]`

### BƯỚC 4: HÌNH ẢNH
Provide both:
- **Tùy chọn 1:** One detailed English prompt for Midjourney/DALL-E style generation.
- **Tùy chọn 2:** One direct cover-image URL if found.

## VIRAL output contract

Unless the user requests another format, return these sections in order:

### BƯỚC 1: GÓC NHÌN CHỦ ĐẠO
- State the selected format: A, B, or C.
- Explain briefly why that format fits the book.
- Extract the key emotional angle, conflict, or insight.

### BƯỚC 2: BÀI VIẾT VIRAL
Write in Vietnamese with these rules:
- Use a sincere, healing, or strongly motivational voice as appropriate.
- Make the text smooth and image-rich, with short mobile-friendly paragraphs.
- Use metaphor, contrast, or emotional truth when helpful.
- Do not sell, do not drop links, do not sound promotional.
- End with either a comment-bait question or a save/share-worthy closing line.

### BƯỚC 3: GỢI Ý VISUAL
- Provide one thematic visual idea or one English AI prompt if a visual would strengthen the post.
- Keep it aligned with the emotional message, not product-heavy.

## Research guidance

Use lightweight web research when the book is not already well known from context.

Prioritize sources in this order:
1. Publisher/product pages
2. Author site or official summaries
3. Reputable review or summary sites
4. Retail/book-listing pages for metadata only

Extract only what is needed:
- title, author
- core theme
- target reader pain points or emotional needs
- 3 memorable lessons or one powerful emotional takeaway
- any strong metaphor or visual concept useful for image generation

Do not overquote copyrighted text. Summarize in your own words. If using a quote in VIRAL mode, keep it short and only when confidence is high.

## Writing heuristics

### AFF heuristics
Optimize for trust, not hype.

Good pattern:
- Hook with a real struggle
- Reframe the problem
- Give 2 to 3 useful takeaways
- Soft recommendation
- Comment-first CTA

Avoid:
- sounding like an ad in the first sentence
- exaggerated claims
- hard-selling language
- long dense blocks
- putting the affiliate URL inside the main post

### VIRAL heuristics
Optimize for resonance, not conversion.

Good pattern:
- Start with a line that feels personally true
- Build recognition and emotional tension fast
- Give one clear shift in perspective
- End on a line that invites reflection, saving, or sharing

Avoid:
- salesy CTA
- explicit product pushing
- too many hashtags
- stiff summary language
- forced virality phrasing

## Image guidance

### AI prompt
Write the prompt in English.
Include:
- subject and metaphor tied to the book's core message
- composition and mood
- style guidance such as 3D isometric, flat design, or cinematic inspirational
- no text in image
- portrait social composition
- `--ar 4:5`

### Preferred generation path
If the environment has native image generation working, use `image_generate`.

If the configured provider is quota-limited or unavailable, prefer an available fallback such as Cloudflare Workers AI when the environment has a valid account token outside the native tool chain.

If generation still fails, return:
- the final prompt
- a cover-image URL if found
- a note that the post can still ship with text-only or cover art

## Facebook posting integration

This skill prepares posting payloads even when the posting mechanism varies across environments.

### If a known Facebook posting skill or tool exists in the environment
- Use it after preparing the content package.
- Confirm the target page(s) and whether the same post should be reused or lightly adapted per page.
- In AFF mode, post the main content first, then publish the first comment with the affiliate link placeholder or provided link.
- In VIRAL mode, post only the main viral post unless the user explicitly requests a comment strategy.

### If no posting tool is directly available
Return a structured payload block for each page:
- page name or identifier
- mode
- post text
- first comment text if AFF mode
- image prompt
- generated image path or cover URL

This lets the caller pipe the result into their own Facebook automation stack.

## Multi-page adaptation

When the user manages multiple pages, adapt lightly rather than rewriting everything from scratch.

Possible variations:
- tone: serious, warm, practical, aspirational, healing
- hook angle: pain point, curiosity, contrarian truth, confession
- CTA wording in AFF mode
- closing question or save/share line in VIRAL mode
- hashtag mix in AFF mode

Keep the core message consistent while avoiding obviously duplicated posts across pages.

## Minimal example structures

### AFF

```markdown
BƯỚC 1: THU THẬP THÔNG TIN
...

BƯỚC 2: VIẾT CONTENT BÀI ĐĂNG
...

BƯỚC 3: BÌNH LUẬN ĐẦU TIÊN
...

BƯỚC 4: HÌNH ẢNH
- Tùy chọn 1: ...prompt...
- Tùy chọn 2: ...cover URL...
```

### VIRAL

```markdown
BƯỚC 1: GÓC NHÌN CHỦ ĐẠO
...

BƯỚC 2: BÀI VIẾT VIRAL
...

BƯỚC 3: GỢI Ý VISUAL
...
```

## References

Read `references/facebook-affiliate-playbook.md` when you need the detailed style rules, page-variation ideas, format ideas, or formatting checklist.