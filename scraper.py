import os
import json
import re
import time
import requests
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
SEEN_FILE = "seen_items.json"
DAILY_LOG = "daily_log.json"
PRICE_MAX = 9000

def load_keywords():
    kw_file = Path("keywords.txt")
    if not kw_file.exists():
        return []
    lines = kw_file.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]

def load_seen():
    if Path(SEEN_FILE).exists():
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_seen(seen: set):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

def load_daily_log():
    if Path(DAILY_LOG).exists():
        with open(DAILY_LOG, "r") as f:
            return json.load(f)
    return []

def save_daily_log(log: list):
    with open(DAILY_LOG, "w") as f:
        json.dump(log, f, ensure_ascii=False)

def make_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,800")
    options.add_argument("--lang=ja-JP")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    return webdriver.Chrome(options=options)

def search_mercari(driver, keyword: str) -> list:
    encoded = quote(keyword)
    url = (
        f"https://jp.mercari.com/search?keyword={encoded}"
        f"&status=on_sale&sort=created_time&order=desc"
        f"&price_max={PRICE_MAX}"
    )
    try:
        driver.get(url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="item-cell"]'))
        )
        time.sleep(1.5)
        items = []
        cells = driver.find_elements(By.CSS_SELECTOR, '[data-testid="item-cell"]')
        for cell in cells:
            try:
                link = cell.find_element(By.CSS_SELECTOR, 'a[href*="/item/"]')
                href = link.get_attribute("href") or ""
                item_id_match = re.search(r'/item/(m\w+)', href)
                if not item_id_match:
                    continue
                item_id = item_id_match.group(1)
                aria = cell.find_element(By.CSS_SELECTOR, '[role="img"]').get_attribute("aria-label") or ""
                price_match = re.search(r'(\d[\d,]+)円', aria)
                price = int(price_match.group(1).replace(",", "")) if price_match else 0
                if price == 0 or price >= PRICE_MAX:
                    continue
                name = re.sub(r'\s*\d[\d,]+円.*$', '', aria).replace("の画像", "").strip()
                if not name:
                    name = "이름 없음"
                items.append({"id": item_id, "name": name, "price": price})
            except Exception:
                continue
        return items
    except Exception as e:
        print(f"  [ERROR] 검색 실패 ({keyword}): {e}")
        return []

def send_telegram(message: str, item_id: str, item_url: str) -> int:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(message)
        return 0
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json().get("result", {}).get("message_id", 0)
    except Exception as e:
        print(f"[ERROR] 텔레그램 전송 실패: {e}")
        return 0

def main():
    keywords = load_keywords()
    if not keywords:
        print("[INFO] keywords.txt 비어있음")
        return

    seen = load_seen()
    daily_log = load_daily_log()
    new_count = 0
    today = datetime.now().strftime("%Y-%m-%d")

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] 검색 시작 — {len(keywords)}개 키워드 / 상한 ¥{PRICE_MAX:,}")

    driver = make_driver()
    try:
        for keyword in keywords:
            print(f"  → 검색 중: {keyword}")
            items = search_mercari(driver, keyword)
            print(f"     {len(items)}개 결과")

            for item in items:
                item_id = item.get("id", "")
                if not item_id or item_id in seen:
                    continue

                seen.add(item_id)
                new_count += 1

                name = item.get("name", "이름 없음")
                price = item.get("price", 0)
                item_url = f"https://jp.mercari.com/item/{item_id}"

                msg = (
                    f"🛍 <b>새 매물 발견!</b>\n"
                    f"🔍 키워드: <code>{keyword}</code>\n"
                    f"📦 {name}\n"
                    f"💴 ¥{price:,}\n"
                    f"🔗 <a href='{item_url}'>메루카리 보기</a>"
                )
                msg_id = send_telegram(msg, item_id, item_url)

                # 데일리 로그에 저장
                daily_log.append({
                    "date": today,
                    "message_id": msg_id,
                    "item_id": item_id,
                    "name": name,
                    "price": price,
                    "url": item_url,
                    "keyword": keyword,
                    "liked": False
                })
                time.sleep(0.3)

            time.sleep(2)
    finally:
        driver.quit()

    save_seen(seen)
    save_daily_log(daily_log)
    print(f"[완료] 새 매물 {new_count}개 발견")

if __name__ == "__main__":
    main()
