import os
import requests
from datetime import datetime

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def get_weather():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=36.402&longitude=138.252&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code&timezone=Asia/Tokyo"
        res = requests.get(url).json()
        
        daily = res['daily']
        max_temp = daily['temperature_2m_max'][0]
        min_temp = daily['temperature_2m_min'][0]
        rain_prob = daily['precipitation_probability_max'][0]
        wmo_code = daily['weather_code'][0]
        
        weather_desc = "맑음 ☀️" if wmo_code == 0 else "구름 조금/흐림 ☁️" if wmo_code <= 3 else "비/눈 🌧️"
        
        return f"🌡️ 우에다 오늘 날씨: {weather_desc}\n📉 최저: {min_temp}°C / 📈 최고: {max_temp}°C\n☔ 강수 확률: {rain_prob}%"
    except:
        return "🌡️ 우에다 날씨: 정보를 가져오지 못했습니다."

def get_fgi():
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://edition.cnn.com/"
        }
        res = requests.get(url, headers=headers)
        data = res.json()
        score = int(data['fear_and_greed']['score'])
        rating = data['fear_and_greed']['rating']
        
        alert = " 🚨" if score <= 20 else ""
        return f"📊 FGI : {score} ({rating}){alert}"
    except:
        return "📊 FGI : 데이터를 가져오지 못했습니다."

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, json=payload)

if __name__ == "__main__":
    weather_info = get_weather()
    fgi_info = get_fgi()
    
    # 오늘 날짜를 '9/24(목)' 형식으로 생성 (요일은 자동으로 한글 변환)
    now = datetime.now()
    days = ['월', '화', '수', '목', '금', '토', '일']
    today_str = f"{now.month}/{now.day}({days[now.weekday()]})"
    
    message = f"🤖 [{today_str}]\n\n{weather_info}\n\n{fgi_info}"
    send_telegram(message)
    print("모닝 브리핑 전송 완료!")
