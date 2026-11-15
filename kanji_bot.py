import os
from datetime import datetime
import pandas as pd
import requests

# --- [설정 구간] 텔레그램 봇 토큰 및 채팅 ID (GitHub Secrets로 관리하는 것을 추천합니다) ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID")

EXCEL_FILE = "今度こそ本気.xlsx"
PROGRESS_FILE = "progress.txt"
BATCH_SIZE = 30  # 하루에 보낼 단어 개수


def load_progress():
  """마지막으로 어디까지 보냈는지 progress.txt에서 읽어옵니다. 없으면 0부터 시작"""
  if os.path.exists(PROGRESS_FILE):
    with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
      try:
        return int(f.read().strip())
      except ValueError:
        return 0
  return 0


def save_progress(index):
  """다음 날 이어서 볼 수 있도록 현재 위치를 저장합니다."""
  with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
    f.write(str(index))


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
  # A열(인덱스 0) = 일본어, E열(인덱스 4) = 한국어 뜻
  if not os.path.exists(EXCEL_FILE):
    print(f"오류: {EXCEL_FILE} 파일을 찾을 수 없습니다.")
    return

  df = pd.read_excel(EXCEL_FILE, header=None)
  total_rows = len(df)

  # 2. 현재 진도 불러오기
  start_idx = load_progress()

  # 만약 끝까지 다 돌았다면(또는 범위를 초과했다면) 0번부터 다시 1회독 시작 (무한 회독)
  if start_idx >= total_rows:
    start_idx = 0

  end_idx = min(start_idx + BATCH_SIZE, total_rows)

  # 3. 30개 단어 추출 (A열: 일본어, E열: 한국어)
  word_list = []
  for i in range(start_idx, end_idx):
    jp_word = df.iloc[i, 0]  # A열
    kr_meaning = df.iloc[i, 4]  # E열
    word_list.append(f"{i+1}. {jp_word} : {kr_meaning}")

  # 4. 요구하신 포맷 만들기 (예: 11/15 [60~90])
  today_date = datetime.now().strftime("%m/%d")
  header_text = f"📚 **{today_date} [{start_idx + 1}~{end_idx}]** (전체 {total_rows}개 중)\n-------------------\n"
  body_text = "\n".join(word_list)
  message = header_text + body_text

  # 5. 텔레그램 전송
  result = send_telegram_message(message)
  if result.get("ok"):
    print("성공적으로 단어 메시지를 전송했습니다.")
    # 6. 다음 진도를 위해 위치 저장 (다음 날은 end_idx부터 시작)
    save_progress(end_idx)
  else:
    print(f"전송 실패: {result}")


if __name__ == "__main__":
  main()
