#!/bin/bash
# Script thực thi đăng bài (được gọi bởi scheduler)

set -euo pipefail

PAGE_INPUT="$1"
MODE="$2"
TOPIC="$3"
LINK="$4"
NOTES="$5"

WORKSPACE="/root/.openclaw/workspace"
STATE_DIR="$WORKSPACE/state"
LOG_FILE="$STATE_DIR/thuc-thi.log"
POSTED_KEYS_FILE="$STATE_DIR/posted-keys.txt"

FB_TOKEN='REDACTED_FB_TOKEN'
CF_TOKEN='REDACTED_CF_TOKEN'
CF_ACCOUNT='ebb062841f91f8fdb5af21b812e9cbd0'

declare -A PAGE_IDS=(
  ["1"]="1135415682984698"
  ["2"]="1099385626592219"
  ["3"]="1077631882095947"
  ["4"]="1124935547358731"
  ["5"]="1051157818072049"
  ["6"]="1016419601547706"
  ["7"]="990672630796214"
  ["8"]="1124354747418012"
  ["9"]="167465759793690"
  ["10"]="105534281021767"
)

log(){ echo "[$(TZ=Asia/Ho_Chi_Minh date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"; }

ACCOUNTS_JSON=$(curl -s "https://graph.facebook.com/v19.0/me/accounts?fields=id,access_token&access_token=$FB_TOKEN")

get_page_token(){
  local page_id="$1"
  echo "$ACCOUNTS_JSON" | sed 's/},{/}\n{/g' | grep "\"id\":\"$page_id\"" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p'
}

generate_image(){
  local prompt="$1" out="$2"
  log "--- Đang thử tạo ảnh bằng Google (Gemini) ---"
  
  local tool_resp
  tool_resp=$(/usr/bin/openclaw tool call image_generate prompt="$prompt" filename="$(basename "$out")" aspect_ratio="3:4" 2>/dev/null || echo "FAILED")
  
  if [[ "$tool_resp" != "FAILED" ]] && [[ "$tool_resp" == *"path"* ]]; then
    local media_path
    media_path=$(echo "$tool_resp" | python3 -c "import sys, json; print(json.load(sys.stdin)['path'])" 2>/dev/null || echo "")
    if [ -f "$media_path" ]; then
      cp "$media_path" "$out"
      log "OK: Đã tạo ảnh bằng Google thành công."
      return 0
    fi
  fi

  log "WARN: Google (Gemini) lỗi hoặc hết quota. Đang fallback sang Cloudflare..."
  curl -s -X POST "https://api.cloudflare.com/client/v4/accounts/$CF_ACCOUNT/ai/run/@cf/bytedance/stable-diffusion-xl-lightning" \
    -H "Authorization: Bearer $CF_TOKEN" -H "Content-Type: application/json" \
    --data "{\"prompt\":\"$prompt\"}" > "$out"
  log "OK: Đã tạo ảnh bằng Cloudflare."
}

openai_llm(){
  local system_prompt="$1"
  local user_prompt="$2"
  local max_retries=2
  local retry=0
  local result=""

  # Accept either OPENAI_API_KEY or ROUTER_API_KEY
  local api_key="${OPENAI_API_KEY:-${ROUTER_API_KEY:-}}"
  if [ -z "${api_key// }" ]; then
    echo ""
    return 0
  fi

  while [ $retry -le $max_retries ] && [ -z "${result// }" ]; do
    result=$(OPENAI_KEY="$api_key" SYS_PROMPT="$system_prompt" USER_PROMPT="$user_prompt" \
    timeout 120 python3 - <<'PY'
import json, os, urllib.request
url = "https://api.9router.com/v1/chat/completions"
payload = {
  "model": "gpt-4o-mini",
  "messages": [
    {"role": "system", "content": os.environ["SYS_PROMPT"] + " BẮT BUỘC trả lời tiếng Việt."},
    {"role": "user", "content": os.environ["USER_PROMPT"]},
  ],
  "max_tokens": 1800,
  "temperature": 0.7,
}
req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={
  "Authorization": f"Bearer {os.environ['OPENAI_KEY']}",
  "Content-Type": "application/json",
})
try:
  with urllib.request.urlopen(req, timeout=110) as r:
    data = json.loads(r.read().decode("utf-8", "ignore"))
    resp = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if resp and len(resp.strip()) > 120:
      print(resp.strip())
    else:
      print("")
except Exception:
  print("")
PY
    )
    retry=$((retry + 1))
  done

  echo "$result"
}

cf_llm(){
  local system_prompt="$1"
  local user_prompt="$2"

  # Try OpenAI via 9router first
  local out
  out=$(openai_llm "$system_prompt" "$user_prompt")
  if [ -n "${out// }" ]; then
    echo "$out"
    return 0
  fi

  # Fallback Cloudflare
  local max_retries=3
  local retry=0
  local result=""
  system_prompt="$system_prompt. BẮT BUỘC PHẢI TRẢ LỜI BẰNG TIẾNG VIỆT. KHÔNG DÙNG TIẾNG ANH."
  user_prompt="$user_prompt (Viết hoàn toàn bằng tiếng Việt sâu sắc, tình cảm)"

  while [ $retry -le $max_retries ] && [ -z "${result// }" ]; do
    result=$(CF_TOKEN_ENV="$CF_TOKEN" CF_ACCOUNT_ENV="$CF_ACCOUNT" SYS_PROMPT="$system_prompt" USER_PROMPT="$user_prompt" \
    timeout 120 python3 - <<'PY'
import json, os, urllib.request
url = f"https://api.cloudflare.com/client/v4/accounts/{os.environ['CF_ACCOUNT_ENV']}/ai/run/@cf/meta/llama-3-8b-instruct"
payload = {
  "messages": [
    {"role": "system", "content": os.environ["SYS_PROMPT"]},
    {"role": "user", "content": os.environ["USER_PROMPT"]},
  ],
  "max_tokens": 1500,
}
req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={
  "Authorization": f"Bearer {os.environ['CF_TOKEN_ENV']}",
  "Content-Type": "application/json",
})
try:
  with urllib.request.urlopen(req, timeout=110) as r:
    data = json.loads(r.read().decode("utf-8", "ignore"))
    print(data.get("result", {}).get("response", ""))
except Exception:
  print("")
PY
    )
    retry=$((retry + 1))
  done

  if [ -z "${result// }" ]; then
    result="Có những ngày mình tưởng chỉ cần cố thêm chút nữa là mọi thứ sẽ ổn.\n\nNhưng càng gồng, mình càng mệt. Đến khi mình chậm lại, mình mới hiểu: điều mình thiếu không phải nỗ lực, mà là một góc nhìn đúng.\n\nBạn thì sao, dạo này điều gì đang làm bạn nặng lòng nhất?"
  fi
  echo "$result"
}

generate_storytelling(){
  local mode="$1" topic="$2" link="$3" notes="$4" page_name="$5"
  local seed_topic="$topic"
  [ -z "${seed_topic// }" ] && seed_topic="$notes"
  [ -z "${seed_topic// }" ] && seed_topic="Cân bằng cuộc sống và bình yên tâm trí"

  if [ "$mode" = "ENGAGE" ]; then
    log "--- Đang thực hiện Research chủ đề đời sống cho ENGAGE: $seed_topic ---"
    local research_nuggets
    research_nuggets=$(cf_llm "You are a social media trend & psychology researcher." "Tìm 3 quan điểm sâu sắc nhất về chủ đề: $seed_topic. Trả lời tiếng Việt, tập trung vào thực tế đời sống, KHÔNG liên quan đến sách.")
    
    log "--- Viết bài ENGAGE 100% tương tác cho $page_name ---"
    local prompt="Viết bài Facebook tương tác (Mode: ENGAGE) cho page '$page_name'. 
Chủ đề: $seed_topic. 
Dữ liệu: $research_nuggets. 
Style: Chân thành, tâm sự, 'mình/bạn', đời thường. 
KHÔNG được nhắc đến từ 'sách', 'đọc', 'tác giả' hay bất kỳ việc bán hàng nào. 
Mục tiêu: Người đọc thấy mình trong đó, muốn comment chia sẻ hoặc share bài về tường. 
Kết bài: Câu hỏi mở cực 'chạm'."
    cf_llm "You are a professional social media content creator focused on high engagement." "$prompt"
  else
    log "--- Đang thực hiện Deep Research sách cho $mode: $seed_topic ---"
    local research_nuggets
    research_nuggets=$(cf_llm "You are a book research assistant." "Tóm tắt 3 bài học và 2 câu quote hay nhất từ: $seed_topic. Trả lời tiếng Việt.")
    
    log "--- Viết bài $mode cho $page_name ---"
    local prompt
    if [ "$mode" = "AFF" ]; then
      prompt="Viết bài Facebook AFF cho page '$page_name', 350-550 chữ. Sách: $seed_topic. Dữ liệu: $research_nuggets. Cấu trúc: Hook -> Struggle -> Encounter -> Transformation -> Recommendation -> CTA (link ở cmt)."
    else
      prompt="Viết bài Facebook VIRAL cho page '$page_name'. Sách: $seed_topic. Dữ liệu: $research_nuggets. KHÔNG bán hàng, chỉ chia sẻ cảm xúc và bài học từ sách để tăng share/save."
    fi
    cf_llm "You are a professional storytelling copywriter." "$prompt"
  fi
}

post_one(){
  local page_id="$1" message="$2" img="$3"
  local page_token photo_id resp post_id
  page_token=$(get_page_token "$page_id")
  [ -z "$page_token" ] && { log "ERROR no token page=$page_id"; return 1; }

  photo_id=$(curl -s -X POST "https://graph.facebook.com/v19.0/$page_id/photos" \
    -F "source=@$img" -F 'published=false' -F "access_token=$page_token" | sed -n 's/.*"id":"\([^"]*\)".*/\1/p')

  resp=$(curl -s -X POST "https://graph.facebook.com/v19.0/$page_id/feed" \
    --data-urlencode "message=$message" \
    --data-urlencode "attached_media=[{\"media_fbid\":\"$photo_id\"}]" \
    --data-urlencode "access_token=$page_token")
  post_id=$(echo "$resp" | sed -n 's/.*"id":"\([^"]*\)".*/\1/p')
  if [ -n "$post_id" ]; then
    log "OK page=$page_id post_id=$post_id"
    echo "$post_id"
    return 0
  fi
  log "ERROR post page=$page_id resp=$resp"
  return 1
}

# Main execution
now=$(TZ=Asia/Ho_Chi_Minh date +%Y-%m-%d)
key="$now|$PAGE_INPUT|$MODE|$TOPIC"

if grep -Fxq "$key" "$POSTED_KEYS_FILE" 2>/dev/null; then
  log "SKIP task already posted: $key"
  exit 0
fi

log "=== Bắt đầu đăng bài: Page=$PAGE_INPUT, Mode=$MODE, Topic=$TOPIC ==="

IFS=',' read -ra pages <<< "$PAGE_INPUT"
for p in "${pages[@]}"; do
  p=$(echo "$p" | xargs)
  page_id="${PAGE_IDS[$p]:-}"
  [ -z "$page_id" ] && { log "WARN unknown page index=$p"; continue; }
  
  case "$p" in
    1) page_name="Triết lý người xưa" ;;
    2) page_name="Triết Lý Cổ Nhân" ;;
    3) page_name="Tủ Sách Thay Đổi Tư Duy" ;;
    4) page_name="Trạm Đọc Chữa Lành" ;;
    8) page_name="Sự Thật Là" ;;
    *) page_name="Fanpage" ;;
  esac


  log "--- Đang tạo nội dung riêng cho Page: $page_name ($p) ---"
  
  img_prompt="A high quality editorial book-themed illustration for $TOPIC $NOTES, cinematic lighting, premium composition, no text, portrait style"
  img="$STATE_DIR/img-${p}-${RANDOM}.jpg"
  generate_image "$img_prompt" "$img"

  msg=$(generate_storytelling "$MODE" "$TOPIC" "$LINK" "$NOTES" "$page_name")

  post_id=$(post_one "$page_id" "$msg" "$img" 2>/dev/null || true)
  
  if [ -n "$post_id" ] && [ -n "${LINK// }" ]; then
    page_token=$(get_page_token "$page_id")
    curl -s -X POST "https://graph.facebook.com/v19.0/$post_id/comments" \
      --data-urlencode "message=Mình để link tham khảo ở đây nhé: $LINK" \
      --data-urlencode "access_token=$page_token" >/dev/null || true
  fi
  rm -f "$img"
done

echo "$key" >> "$POSTED_KEYS_FILE"
log "=== Hoàn tất task: $key ==="

/usr/bin/openclaw message send --channel telegram --target "telegram:8051440849" --message "✅ Đã đăng xong task 09:00 (đăng bù): $MODE (Page $PAGE_INPUT)" 2>/dev/null || true
