import os
import requests

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def get_weather():
    try:
        # 오늘 하루 일일 예보(최고/최저 기온, 강수 확률 등)를 가져오도록 API 호출 수정
        url = "https://api.open-meteo.com/v1/forecast?latitude=36.402&longitude=138.252&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code&timezone=Asia/Tokyo"
        res = requests.get(url).json()
        
        daily = res['daily']
        max_temp = daily['temperature_2m_max'][0] # 오늘 최고기온
        min_temp = daily['temperature_2m_min'][0] # 오늘 최저기온
        rain_prob = daily['precipitation_probability_max'][0] # 오늘 강수 확률(%)
        wmo_code = daily['weather_code'][0]
        
        # 날씨 상태 아이콘 및 설명
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
        buy_signal = "🚨 [SPY 1단계 매수 룰 발동 구간!]" if score <= 20 else "💤 관망 구간"
        return f"📊 FGI : {score} ({rating})\n{buy_signal}"
    except:
        return "📊 FGI : 데이터를 가져오지 못했습니다."

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, json=payload)

if __name__ == "__main__":
    weather_info = get_weather()
    fgi_info = get_fgi()
    message = f"🤖 [Manpuki 모닝 브리핑]\n\n{weather_info}\n\n{fgi_info}"
    send_telegram(message)
    print("모닝 브리핑 전송 완료!")
