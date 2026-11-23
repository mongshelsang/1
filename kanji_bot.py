from datetime import datetime, timedelta, timezone
import os
import pandas as pd
import requests

# 깃허브 시크릿 이름(TELEGRAM_TOKEN)과 정확히 일치하도록 설정
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID")

EXCEL_FILE = "今度こそ本気.xlsx"
BATCH_SIZE = 10  # 하루에 보낼 단어 개수 (30 -> 20으로 변경)


def send_telegram_message(message):
  """텔레그램 메시지 전송 함수"""
  url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
  payload = {
      "chat_id": TELEGRAM_CHAT_ID,
      "text": message,
      "parse_mode": "Markdown",
  }
  response = requests.post(url, json=payload)
  return response.json()


def main():
  # 1. 엑셀 파일 읽기 (pandas 사용)
  if not os.path.exists(EXCEL_FILE):
    print(f"오류: {EXCEL_FILE} 파일을 찾을 수 없습니다.")
    return

  df = pd.read_excel(EXCEL_FILE, header=None)
  total_rows = len(df)

  # 2. 한국/일본 시간(UTC+9) 기준 오늘(11/22)부터 1~20번이 나오도록 기준일 설정
  jst = timezone(timedelta(hours=9))
  start_date = datetime(2026, 11, 22, tzinfo=jst)
  today = datetime.now(jst)
  days_passed = (today.date() - start_date.date()).days

  if days_passed < 0:
    days_passed = 0

  # 경과일에 따라 시작 인덱스 자동 계산 (무한 회독 가능하도록 나머지 연산 사용)
  start_idx = (days_passed * BATCH_SIZE) % total_rows
  end_idx = min(start_idx + BATCH_SIZE, total_rows)

  if start_idx >= total_rows:
    start_idx = 0
    end_idx = min(BATCH_SIZE, total_rows)

  # 3. 20개 단어 추출 (E열: 한국어 뜻만 추출, 일본어 제외)
  word_list = []
  for i in range(start_idx, end_idx):
    kr_meaning = df.iloc[i, 4]  # E열 (한국어 뜻)
    word_list.append(f"{i+1}. {kr_meaning}")

  # 4. 포맷 만들기
  today_date = today.strftime("%m/%d")
  header_text = (
      f"📚 **{today_date} [{start_idx + 1}~{end_idx}]** (전체 {total_rows}개 중)\n"
      "-------------------\n"
  )
  body_text = "\n".join(word_list)
  message = header_text + body_text

  # 5. 텔레그램 전송
  result = send_telegram_message(message)
  if result.get("ok"):
    print("성공적으로 한국어 뜻 단어 메시지를 전송했습니다.")
  else:
    print(f"전송 실패: {result}")


if __name__ == "__main__":
  main()
