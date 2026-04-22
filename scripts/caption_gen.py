import json
import os
import sys

# Add local path to ensure we can read our files
ROOT = "/root/.openclaw/workspace"
PLAN_PATH = os.path.join(ROOT, "output/daily-plan.json")
CONFIG_PATH = os.path.join(ROOT, "config/pages.json")

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_captions():
    plan = load_json(PLAN_PATH)
    config = load_json(CONFIG_PATH)
    page_map = {p['page_id']: p for p in config['pages']}
    
    for post in plan['posts']:
        if post['caption']: continue
        
        page_cfg = page_map.get(post['page_id'])
        prompt = f"""Viết caption Facebook cho trang '{post['page_name']}'.
Persona: {page_cfg['persona']}
Audience: {page_cfg['audience']}
Loại bài: {post['post_type']}
Sách: {post['product_title']}
Link: {post['affiliate_link']}

Yêu cầu:
- Hook mạnh ở dòng đầu.
- Nội dung sâu sắc, tình cảm hoặc thực tế tùy persona.
- Không dùng dấu *.
- Không dùng tiếng Anh (trừ tên sách nếu cần).
- Không chia đề mục máy móc (CTA, Chuyển đổi...).
- Có câu disclosure: 'link affiliate'.
- Hashtags: {', '.join(page_cfg['hashtags'])}
"""
        # We trigger the LLM call via the main agent turn instead of raw requests here
        # to ensure it follows the "System Prompt" exactly.
        # For this script, we just mark it as needing content.
        print(f"--- REQUEST_CAPTION_FOR: {post['page_id']} | {post['product_title']} ---")
        print(prompt)
        print("--- END_REQUEST ---")

if __name__ == "__main__":
    generate_captions()
