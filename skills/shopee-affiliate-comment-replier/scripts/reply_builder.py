#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import random
import re
from contextlib import contextmanager
from pathlib import Path
import fcntl

from facebook_api import create_comment_reply, FacebookApiError

NO_LINK_REPLY = "Dạ bạn đợi chút xíu, mình đang kiểm tra lại link sản phẩm và sẽ gửi bạn ngay nhé ạ! Cảm ơn bạn quan tâm."
SKIP_ALREADY_REPLIED = "__SKIP_ALREADY_REPLIED__"
SEND_OK = "__SEND_OK__"

LINK_RE = re.compile(r'https?://(?:s\.shopee\.vn|shopee\.vn|shope\.ee|shp\.ee|shpe\.ee)/[^\s\]\[\)\(\}"\'<>]+', re.IGNORECASE)
PHONE_RE = re.compile(r"(?:\+?84|0)(?:\d[ .-]?){8,10}")
TRAILING_LINK_PUNCT = '.,;:!?)]}"\''
STATE_PATH = Path(__file__).resolve().parent.parent / 'replied_customers.json'
LOCK_PATH = Path(__file__).resolve().parent.parent / 'replied_customers.lock'

REPLY_POOLS = {
    'ask_link': [
        "Dạ mình chào bạn ạ, mình gửi bạn link sản phẩm đây nha: {link} Bạn nhấp vào link để xem chi tiết và đặt hàng giúp mình nhé!",
        "Chào bạn nha, mình để link sản phẩm ngay đây ạ: {link} Bạn bấm vào xem mẫu và chốt đơn tiện hơn giúp mình nha!",
        "Dạ shop chào bạn, link sản phẩm mình gửi bạn ở đây nè: {link} Bạn vào xem chi tiết rồi đặt hàng giúp shop nha!",
    ],
    'ask_price': [
        "Dạ shop chào bạn, để check giá đang sale và các ưu đãi thì bạn nhấp vào link này nha: {link} Bạn vào xem đúng giá tại thời điểm này giúp mình ạ!",
        "Dạ mình chào bạn ạ, giá bên Shopee sẽ cập nhật theo chương trình đang chạy trong link này nè: {link} Bạn bấm vào xem giúp mình nha!",
        "Chào bạn nha, mình gửi bạn link để xem giá và voucher hiện tại luôn ạ: {link} Bạn vào đó sẽ thấy giá đang áp dụng trực tiếp nha!",
    ],
    'ask_attribute': [
        "Dạ mình chào bạn ạ, thông tin về size, màu và chất liệu shop để khá đầy đủ trong link này nè: {link} Bạn bấm vào xem chi tiết rồi cần mình hỗ trợ thêm thì nhắn mình nha!",
        "Dạ shop chào bạn, phần size, màu, chất vải và thông tin ship shop có ghi rõ trong link này ạ: {link} Bạn tham khảo giúp mình nha!",
        "Chào bạn nha, mình gửi bạn link sản phẩm để xem kỹ bảng size, màu và mô tả chất liệu đây ạ: {link} Bạn cần mình gợi ý thêm thì nhắn mình ngay nha!",
    ],
    'praise': [
        "Chào bạn nha, cảm ơn bạn nhiều ạ, mẫu này bên mình được hỏi khá nhiều luôn: {link} Bạn tham khảo thử trong link giúp mình nha!",
        "Dạ mình chào bạn ạ, cảm ơn bạn khen dễ thương quá nè, mẫu này lên form xinh lắm ạ: {link} Bạn xem thử giúp mình nha!",
        "Dạ shop chào bạn, cảm ơn bạn nhiều nha, mẫu này đang khá hot bên mình đó ạ: {link} Bạn bấm vào xem chi tiết giúp shop nha!",
    ],
    'phone_number': [
        "Dạ mình chào bạn ạ, để bảo mật thông tin thì bạn hạn chế để lại SĐT công khai nha. Bạn nhấp vào link Shopee này giúp mình để xem và đặt hàng an toàn hơn ạ: {link}",
        "Dạ shop chào bạn, mình xin phép nhắc nhẹ là bạn không nên để số điện thoại ở bình luận công khai nha ạ. Bạn vào link Shopee này để đặt hàng và áp mã tiện hơn giúp shop nhé: {link}",
        "Chào bạn nha, để bảo mật thông tin cá nhân thì mình khuyên bạn hạn chế để lại SĐT dưới comment ạ. Bạn bấm vào link Shopee này để xem hàng và đặt đơn giúp mình nha: {link}",
    ],
    'strong_buy': [
        "Dạ mình chào bạn ạ, mẫu này bên mình đang khá hot và nhiều bạn chốt lắm nha: {link} Bạn đặt sớm giúp mình để giữ mẫu đẹp và ưu đãi hiện tại nha!",
        "Dạ shop chào bạn, bạn chốt nhanh qua link này giúp mình nha: {link} Mã này đang được hỏi nhiều nên bạn tranh thủ đặt sớm để giữ hàng ạ!",
        "Chào bạn nha, mình gửi bạn link chốt đơn ngay đây ạ: {link} Bạn bấm đặt sớm giúp mình kẻo lỡ size hoặc màu đẹp nha!",
    ],
    'generic': [
        "Dạ shop chào bạn, mình gửi bạn link sản phẩm để tiện tham khảo nè: {link} Bạn vào xem chi tiết rồi cần mình tư vấn thêm thì nhắn mình ngay nha!",
        "Dạ mình chào bạn ạ, mình để link sản phẩm ở đây cho bạn tiện xem nha: {link} Bạn cần hỏi gì thêm thì cứ nhắn mình ạ!",
        "Chào bạn nha, mình gửi bạn link sản phẩm đây ạ: {link} Bạn bấm vào xem chi tiết giúp mình nha!",
    ],
}


@contextmanager
def state_lock():
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open('w') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {'replied': {}}
    try:
        data = json.loads(STATE_PATH.read_text(encoding='utf-8'))
        if isinstance(data, dict) and isinstance(data.get('replied'), dict):
            return data
    except Exception:
        pass
    return {'replied': {}}


def save_state(data: dict):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def has_replied(post_id: str, customer_id: str, state: dict) -> bool:
    if not post_id or not customer_id:
        return False
    return str(customer_id) in state.get('replied', {}).get(str(post_id), [])


def mark_replied(post_id: str, customer_id: str, state: dict):
    if not post_id or not customer_id:
        return
    replied = state.setdefault('replied', {})
    bucket = replied.setdefault(str(post_id), [])
    if str(customer_id) not in bucket:
        bucket.append(str(customer_id))


def extract_link(post_content: str) -> str:
    text = post_content or ""
    for match in LINK_RE.finditer(text):
        link = match.group(0).strip().rstrip(TRAILING_LINK_PUNCT)
        if any(host in link.lower() for host in ['s.shopee.vn', 'shopee.vn', 'shope.ee', 'shp.ee', 'shpe.ee']):
            return link
    return ""


def classify(comment: str) -> str:
    c = (comment or "").strip().lower()
    if not c:
        return "generic"

    if PHONE_RE.search(c):
        return 'phone_number'

    if any(k in c for k in ["chốt nha", "chốt luôn", "lấy mình", "lấy em", "mình lấy", "em lấy", "mua luôn", "đặt luôn", "order luôn", "chốt đơn"]):
        return 'strong_buy'

    if c in {".", "..", "...", ",", "chấm", "ib", "ib ạ", "ib shop", "link"}:
        return "ask_link"
    if any(k in c for k in ["xin link", "cho mình xin link", "cho em xin link", "cho xin link", "gửi link", "pass link", "thả link", "xin in4", "xin info"]):
        return "ask_link"

    if any(k in c for k in ["giá", "bao nhiêu", "bn", "giá sao", "giá ntn", "còn sale không", "bao tiền"]):
        return "ask_price"

    if any(k in c for k in ["size", "màu", "mau", "chất", "chất liệu", "vải", "form", "ship", "freeship", "cod", "đổi trả", "bảo hành"]):
        return "ask_attribute"

    if any(k in c for k in ["đẹp", "xinh", "ưng", "ok", "xịn", "tuyệt", "iu", "yêu", "❤️", "😍", "👍", "🔥", "🥰", "👏"]):
        return "praise"

    return "generic"


def build_reply(post_content: str, customer_comment: str, post_id: str = '', customer_id: str = '') -> str:
    with state_lock():
        state = load_state()
        if has_replied(post_id, customer_id, state):
            return SKIP_ALREADY_REPLIED

        link = extract_link(post_content)
        if not link:
            return NO_LINK_REPLY

        intent = classify(customer_comment)
        pool = REPLY_POOLS.get(intent) or REPLY_POOLS['generic']
        reply = random.choice(pool).format(link=link)
        mark_replied(post_id, customer_id, state)
        save_state(state)
        return reply


def build_and_send_reply(post_content: str, customer_comment: str, comment_id: str, post_id: str = '', customer_id: str = '', send_live: bool = True) -> str:
    reply = build_reply(post_content, customer_comment, post_id, customer_id)
    if reply == SKIP_ALREADY_REPLIED:
        print(f"[SKIP] Already replied for post_id={post_id} customer_id={customer_id}")
        return reply
    if reply == NO_LINK_REPLY:
        print(f"[SKIP] No Shopee link found in post_content for post_id={post_id}")
        return reply

    if not send_live:
        print(f"[SEND_OK][MOCK] comment_id={comment_id} reply_text={reply}")
        return SEND_OK

    try:
        resp = create_comment_reply(comment_id, reply)
        print(f"[SEND_OK] comment_id={comment_id} reply_id={resp.get('id','')}")
        return SEND_OK
    except FacebookApiError as e:
        print(f"[SEND_ERROR] comment_id={comment_id} error={e}")
        return f"__SEND_ERROR__:{e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--post-content", required=True)
    ap.add_argument("--comment", required=True)
    ap.add_argument("--post-id", default='')
    ap.add_argument("--customer-id", default='')
    ap.add_argument("--comment-id", default='')
    ap.add_argument("--send", action='store_true')
    args = ap.parse_args()
    if args.send:
        if not args.comment_id:
            raise SystemExit('--send requires --comment-id')
        print(build_and_send_reply(args.post_content, args.comment, args.comment_id, args.post_id, args.customer_id))
    else:
        print(build_reply(args.post_content, args.comment, args.post_id, args.customer_id))


if __name__ == "__main__":
    main()
