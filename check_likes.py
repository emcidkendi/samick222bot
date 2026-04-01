import os
import json
import re
import requests
from pathlib import Path

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHANNEL_ID = "-1003882080903"  # 이크에크 채널
SHEETS_URL = "https://script.google.com/macros/s/AKfycbxscQ1bE4BOitDfbAY2MPISbxpP3lx_nJsBuZJXCN_h3WYfoIpV0FaFnkvGTR0NAi7F/exec"
OFFSET_FILE = "callback_offset.json"

def load_offset():
    if Path(OFFSET_FILE).exists():
        with open(OFFSET_FILE, "r") as f:
            return json.load(f).get("offset", 0)
    return 0

def save_offset(offset):
    with open(OFFSET_FILE, "w") as f:
        json.dump({"offset": offset}, f)

def add_to_sheets(price, url):
    try:
        resp = requests.post(SHEETS_URL, json={"price": price, "url": url}, timeout=10)
        print(f"  ✅ 시트 추가: ¥{price:,} → {resp.status_code}")
    except Exception as e:
        print(f"  [ERROR] 시트 추가 실패: {e}")

def main():
    if not TELEGRAM_TOKEN:
        print("[INFO] 토큰 없음")
        return

    offset = load_offset()

    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates",
            params={"offset": offset, "timeout": 5},
            timeout=10
        )
        updates = resp.json().get("result", [])
    except Exception as e:
        print(f"[ERROR] 업데이트 실패: {e}")
        return

    if not updates:
        print("[INFO] 새 업데이트 없음")
        return

    new_count = 0

    for update in updates:
        save_offset(update["update_id"] + 1)

        # 이크에크 채널에 새 메시지 감지
        channel_post = update.get("channel_post")
        if not channel_post:
            continue

        chat_id = str(channel_post.get("chat", {}).get("id", ""))
        if chat_id != CHANNEL_ID:
            continue

        # 메시지에서 URL과 가격 추출
        text = channel_post.get("text", "")
        entities = channel_post.get("entities", [])

        # URL 추출 (text_link 엔티티에서)
        url = None
        for entity in entities:
            if entity.get("type") == "text_link":
                url = entity.get("url", "")
                if "mercari" in url:
                    break

        # 가격 추출 (¥숫자 패턴)
        price_match = re.search(r'¥([\d,]+)', text)
        price = int(price_match.group(1).replace(",", "")) if price_match else 0

        if url and price:
            print(f"  📥 이크에크 새 메시지 감지: ¥{price:,}")
            add_to_sheets(price, url)
            new_count += 1

    print(f"[완료] {new_count}개 시트 등록됨")

if __name__ == "__main__":
    main()
