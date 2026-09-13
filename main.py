import os
import requests
import json

# 1. 获取环境变量
ODDS_API_KEY = os.environ.get("ODDS_API_KEY")
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")

def fetch_and_parse_odds():
    url = "https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?apiKey=" + ODDS_API_KEY + "&regions=eu&markets=h2h"
    response = requests.get(url)
    if response.status_code != 200:
        return "获取赔率数据失败，状态码：" + str(response.status_code)
    
    try:
        data = response.json()
    except Exception as e:
        return "解析赔率数据出错：" + str(e)
    
    if not data or not isinstance(data, list):
        return "当前暂无英超比赛赔率数据。"

    # 开始对比赛数据进行美观排版
    message_lines = ["⚽ *英超最新赛事赔率播报* ⚽\n"]
    
    # 限制最多显示前 5 场比赛，避免消息过长
    for match in data[:5]:
        home = match.get("home_team", "主队")
        away = match.get("away_team", "客队")
        commence_time = match.get("commence_time", "").replace("T", " ")[:16]
        
        message_lines.append(f"📌 *{home} vs {away}*")
        message_lines.append(f"🕒 时间: `{commence_time}`")
        
        bookmakers = match.get("bookmakers", [])
        if bookmakers:
            # 取第一家博彩公司的赔率作为参考
            markets = bookmakers[0].get("markets", [])
            for market in markets:
                if market.get("key") == "h2h":
                    outcomes = market.get("outcomes", [])
                    odds_str = " | ".join([f"{o.get('name')}: `{o.get('price')}`" for o in outcomes])
                    message_lines.append(f"💰 欧赔: {odds_str}")
        message_lines.append("-----------------------------------")
        
    return "\n".join(message_lines)

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)

if __name__ == "__main__":
    print("开始获取并解析足球数据...")
    formatted_data = fetch_and_parse_odds()
    print("推送到 Telegram...")
    send_telegram_message(formatted_data)
    print("推送完成！")
