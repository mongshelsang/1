from datetime import datetime
import os
import time
import requests

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def get_weather():
  url = "https://api.open-meteo.com/v1/forecast?latitude=36.402&longitude=138.252&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code&timezone=Asia/Tokyo"

  # 최대 3번까지 재시도 (실패 시 2초 대기 후 재시도)
  for attempt in range(3):
    try:
      res = requests.get(url, timeout=5)
      if res.status_code == 200:
        data = res.json()
        daily = data["daily"]
        max_temp = daily["temperature_2m_max"][0]
        min_temp = daily["temperature_2m_min"][0]
        rain_prob = daily["precipitation_probability_max"][0]
        wmo_code = daily["weather_code"][0]

        weather_desc = (
            "맑음 ☀️"
            if wmo_code == 0
            else "구름 조금/흐림 ☁️"
            if wmo_code <= 3
            else "비/눈 🌧️"
        )

        return (
            f"🌡️ 우에다 날씨: {weather_desc}\n📉 최저:"
            f" {min_temp}°C / 📈 최고: {max_temp}°C\n☔ 강수 확률:"
            f" {rain_prob}%"
        )
    except Exception:
      pass

    # 실패해서 다음 시도로 넘어가기 전에 2초 대기 (서버 부하 완화)
    time.sleep(2)

  return "🌡️ 우에다 날씨: 정보를 가져오지 못했습니다."


def get_fgi():
  try:
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
            " like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://edition.cnn.com/",
    }
    res = requests.get(url, headers=headers, timeout=5)
    data = res.json()
    score = int(data["fear_and_greed"]["score"])
    rating = data["fear_and_greed"]["rating"]

    alert = " 🚨" if score <= 20 else ""
    return f"📊 FGI : {score} ({rating}){alert}"
  except Exception:
    return "📊 FGI : 데이터를 가져오지 못했습니다."


def send_telegram(message):
  url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
  payload = {"chat_id": CHAT_ID, "text": message}
  requests.post(url, json=payload)


if __name__ == "__main__":
  weather_info = get_weather()
  fgi_info = get_fgi()

  now = datetime.now()
  days = ["월", "화", "수", "목", "금", "토", "일"]
  today_str = f"{now.month}/{now.day}({days[now.weekday()]})"

  message = f"🤖 {today_str}\n\n{weather_info}\n\n{fgi_info}"
  send_telegram(message)
  print("모닝 브리핑 전송 완료!")
