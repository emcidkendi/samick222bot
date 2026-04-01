"""
매일 밤 11시 실행 — ❤️ 누른 매물만 추려서 Gmail로 발송
"""
import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from pathlib import Path

GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_PASS = os.environ.get("GMAIL_PASS", "")
DAILY_LOG = "daily_log.json"

def load_daily_log():
    if Path(DAILY_LOG).exists():
        with open(DAILY_LOG, "r") as f:
            return json.load(f)
    return []

def save_daily_log(log: list):
    with open(DAILY_LOG, "w") as f:
        json.dump(log, f, ensure_ascii=False)

def send_email(liked_items: list, today: str):
    if not GMAIL_USER or not GMAIL_PASS:
        print("[WARN] Gmail 설정 없음")
        return

    subject = f"[SAMICK] ❤️ 오늘의 저장 목록 — {today} ({len(liked_items)}개)"

    # HTML 이메일 본문
    rows = ""
    for i, item in enumerate(liked_items, 1):
        rows += f"""
        <tr style="border-bottom:1px solid #222;">
          <td style="padding:12px;color:#888;font-size:12px;">{i}</td>
          <td style="padding:12px;font-size:13px;">{item['name']}</td>
          <td style="padding:12px;color:#c9a84c;font-weight:bold;">¥{item['price']:,}</td>
          <td style="padding:12px;font-size:11px;color:#888;">{item['keyword']}</td>
          <td style="padding:12px;">
            <a href="{item['url']}" style="color:#c9a84c;text-decoration:none;font-size:12px;">보기 →</a>
          </td>
        </tr>
        """

    html = f"""
    <html>
    <body style="background:#080808;color:#e8e8e8;font-family:'Courier New',monospace;padding:40px;">
      <h1 style="font-size:28px;letter-spacing:0.1em;color:#f0f0f0;">
        SAMICK<span style="color:#c9a84c;">429</span>
      </h1>
      <p style="color:#888;font-size:12px;letter-spacing:0.15em;">DAILY SAVED ITEMS — {today}</p>
      <br>
      <table style="width:100%;border-collapse:collapse;background:#111;">
        <thead>
          <tr style="border-bottom:1px solid #333;">
            <th style="padding:12px;text-align:left;color:#444;font-size:10px;letter-spacing:0.2em;">#</th>
            <th style="padding:12px;text-align:left;color:#444;font-size:10px;letter-spacing:0.2em;">ITEM</th>
            <th style="padding:12px;text-align:left;color:#444;font-size:10px;letter-spacing:0.2em;">PRICE</th>
            <th style="padding:12px;text-align:left;color:#444;font-size:10px;letter-spacing:0.2em;">KEYWORD</th>
            <th style="padding:12px;text-align:left;color:#444;font-size:10px;letter-spacing:0.2em;">LINK</th>
          </tr>
        </thead>
        <tbody>
          {rows}
        </tbody>
      </table>
      <br>
      <p style="color:#333;font-size:10px;letter-spacing:0.1em;">SAMICK VINTAGE INTELLIGENCE SYSTEM</p>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = GMAIL_USER
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASS)
            server.sendmail(GMAIL_USER, GMAIL_USER, msg.as_string())
        print(f"[완료] 메일 발송 완료 — {len(liked_items)}개 항목")
    except Exception as e:
        print(f"[ERROR] 메일 발송 실패: {e}")

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    daily_log = load_daily_log()

    # 오늘 날짜 + ❤️ 누른 것만
    liked_items = [
        item for item in daily_log
        if item.get("liked") and item.get("date") == today
    ]

    print(f"[{today}] 저장된 항목: {len(liked_items)}개")

    if not liked_items:
        print("[INFO] 오늘 저장된 항목 없음 — 메일 발송 안 함")
        return

    send_email(liked_items, today)

    # 오래된 로그 정리 (7일 이상된 것 삭제)
    cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    daily_log = [item for item in daily_log if item.get("date", "") >= cutoff]
    save_daily_log(daily_log)

if __name__ == "__main__":
    main()
