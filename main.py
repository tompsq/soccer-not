import os
import requests

# 1. 获取环境变量
ODDS_API_KEY = os.environ.get("ODDS_API_KEY")
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")

def fetch_soccer_odds():
    url = "https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?apiKey=" + ODDS_API_KEY + "&regions=eu&markets=h2h"
    response = requests.get(url)
    if response.status_code != 200:
        return "获取赔率数据失败，状态码：" + str(response.status_code)
    
    # 稍微截取并处理一下原始数据，让它适合在 Telegram 显示
    raw_text = response.text
    if len(raw_text) > 3500:
        raw_text = raw_text[:3500] + "\n...(内容较长已截断)"
    return "⚽ **英超赔率最新数据推送** ⚽\n\n```json\n" + raw_text + "\n```"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)

if __name__ == "__main__":
    print("开始获取足球数据...")
    data = fetch_soccer_odds()
    print("推送到 Telegram...")
    send_telegram_message(data)
    print("推送完成！")
