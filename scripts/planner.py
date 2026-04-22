import json
import csv
import os
import random
import hashlib
from datetime import datetime, timedelta

# Paths
ROOT = "/root/.openclaw/workspace"
DATA_PATH = os.path.join(ROOT, "data/products.csv")
CONFIG_PATH = os.path.join(ROOT, "config/pages.json")
HISTORY_PATH = os.path.join(ROOT, "state/posting-history.json")
OUTPUT_PATH = os.path.join(ROOT, "output/daily-plan.json")

def load_data():
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
    
    products = []
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['status'] == 'active' and row['affiliate_link']:
                products.append(row)
                
    with open(HISTORY_PATH, 'r') as f:
        history_data = json.load(f)
        
    return config, products, history_data

def get_posted_products(history_data, page_id, days):
    cutoff = datetime.now() - timedelta(days=days)
    posted = set()
    for entry in history_data['history']:
        if entry['page_id'] == page_id:
            try:
                posted_at = datetime.fromisoformat(entry['posted_at'].replace('Z', '+00:00'))
                # Handle timezone if needed, here just comparing
                if posted_at > cutoff:
                    posted.add(entry['product_id'])
            except:
                continue
    return posted

def select_product(products, page_cfg, already_posted):
    # Filter by priority categories first
    pool = [p for p in products if p['category'] in page_cfg['priority_categories'] and p['product_id'] not in already_posted]
    
    # Fallback to any active product if pool is empty
    if not pool:
        pool = [p for p in products if p['product_id'] not in already_posted]
    
    if not pool:
        return None
        
    # Weight by priority_score
    pool.sort(key=lambda x: int(x.get('priority_score', 5)), reverse=True)
    return random.choice(pool[:5]) # Choose one from top 5 prioritized

def fingerprint_text(text):
    return hashlib.md5(text.strip().lower().encode('utf-8')).hexdigest()[:16]

def generate_draft_caption(page_name, persona, post_type, product_title, affiliate_link, hashtags):
    if post_type == "soft_content":
        content = (
            f"Có những cuốn sách không đọc để biết thêm, mà đọc để hiểu mình hơn.\n\n"
            f"{product_title} là kiểu sách như vậy: nhẹ nhàng nhưng đủ sâu để mình dừng lại, nhìn lại cách sống và cách đối xử với chính mình.\n\n"
            f"Nếu dạo này bạn muốn chậm lại một chút để sắp xếp lại tâm trí, có thể tham khảo cuốn này."
        )
    else:
        content = (
            f"Nếu bạn đang tìm một cuốn sách vừa dễ đọc vừa có giá trị áp dụng ngay, {product_title} là lựa chọn rất đáng cân nhắc.\n\n"
            f"Nội dung thực tế, rõ ràng, đọc xong có thể áp dụng từng ý nhỏ vào cuộc sống hằng ngày.\n\n"
            f"Mình để link tham khảo bên dưới cho bạn nào cần."
        )
    
    caption = (
        f"{content}\n\n"
        f"Tham khảo tại đây: {affiliate_link}\n"
        f"{hashtags}\n"
        f"link affiliate"
    )
    return caption

def generate_plan():
    config, products, history_data = load_data()
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    daily_plan = {
        "generated_at": datetime.now().isoformat(),
        "publish_mode": config.get("publish_mode", False),
        "date": today_str,
        "posts": []
    }
    
    existing_fingerprints = set(h.get('caption_fingerprint') for h in history_data.get('history', []) if h.get('caption_fingerprint'))

    for page in config['pages']:
        page_id = page['page_id']
        cooldown = page.get('cooldown_days_same_product', 14)
        posted_recent = get_posted_products(history_data, page_id, cooldown)
        
        # Simple alternation or random assignment of types
        types = page['allowed_post_types']
        
        for i in range(min(page['posts_per_day'], len(page['time_slots']))):
            product = select_product(products, page, posted_recent)
            if not product:
                continue
                
            posted_recent.add(product['product_id'])
            post_type = "soft_content" if i == 0 else "direct_sell"
            if post_type not in types: post_type = types[0]
            
            hashtag_line = " ".join(page.get('hashtags', [])[:5])
            caption = generate_draft_caption(
                page_name=page['page_name'],
                persona=page['persona'],
                post_type=post_type,
                product_title=product['title'],
                affiliate_link=product['affiliate_link'],
                hashtags=hashtag_line
            )
            fp = fingerprint_text(caption)
            if fp in existing_fingerprints:
                caption += "\n\nGóc nhìn hôm nay: đọc để thay đổi từ những điều nhỏ nhất."
                fp = fingerprint_text(caption)
            existing_fingerprints.add(fp)

            daily_plan["posts"].append({
                "page_id": page_id,
                "page_name": page["page_name"],
                "post_type": post_type,
                "product_id": product["product_id"],
                "product_title": product["title"],
                "scheduled_time": f"{today_str} {page['time_slots'][i]}",
                "caption": caption,
                "affiliate_link": product["affiliate_link"],
                "status": "ready_to_publish",
                "meta": {
                    "caption_fingerprint": fp,
                    "publish_mode": config.get("publish_mode", False)
                }
            })
            
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(daily_plan, f, indent=2, ensure_ascii=False)
    
    return daily_plan

if __name__ == "__main__":
    plan = generate_plan()
    print(f"Generated plan with {len(plan['posts'])} posts.")
