import datetime
import os
import random
import pandas as pd
import requests

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def send_telegram_message(message):
  url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
  payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
  requests.post(url, json=payload)


def main():
  excel_path = "今度こそ本気.xlsx"
  if not os.path.exists(excel_path):
    print("엑셀 파일을 찾을 수 없습니다.")
    return

  df = pd.read_excel(excel_path, header=None)

  sample_size = min(5, len(df))
  selected_rows = df.sample(n=sample_size)

  # 오늘 날짜 구하기
  today = datetime.date.today().strftime("%Y년 %m월 %d일")

  msg = f"📅 {today}\n\n"

  for i, (idx, row) in enumerate(selected_rows.iterrows(), 1):
    # K열(인덱스 10)의 한글 뜻만 가져오기
    meaning = row.iloc[10] if len(row) > 10 else "뜻 없음"

    if pd.isna(meaning):
      meaning = ""

    # 한자(A열)는 제외하고 번호와 한글 뜻만 출력
    msg += f"{i}. {meaning}\n"

  send_telegram_message(msg)


if __name__ == "__main__":
  main()
