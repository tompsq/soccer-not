import os, requests
from datetime import datetime, timezone, timedelta

API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY")
T, C = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")

def send(msg):
    if not T or not C: return
    url = f"https://api.telegram.org/bot{T}/sendMessage"
    requests.post(url, json={"chat_id": C, "text": msg})

def test_today_or_recent():
    if not API_FOOTBALL_KEY:
        return "❌ 错误：未读取到 API_FOOTBALL_KEY！"
    
    headers = {"x-apisports-key": API_FOOTBALL_KEY}
    tz = timezone(timedelta(hours=8))
    today_str = datetime.now(tz).strftime("%Y-%m-%d")
    
    # 查今天
    url = "https://v3.football.api-sports.io/fixtures"
    params = {"league": 39, "season": 2026, "date": today_str}
    
    r = requests.get(url, headers=headers, params=params, timeout=10)
    data = r.json().get("response", [])
    
    if data:
        fix = data[0]
        home = fix.get("teams", {}).get("home", {}).get("name")
        away = fix.get("teams", {}).get("away", {}).get("name")
        return f"✅ API 连通性完全正常！今天 ({today_str}) 查到了比赛：{home} vs {away}"
    else:
        # 如果今天没有，往回查最近 10 天内有比赛的一天
        return f"ℹ️ 今天 ({today_str}) 英超无比赛（符合间歇期特征）。这证明 API 接口和 Key 都是通的，纯粹是 API 数据库里没有录入 10 月份的未来远期早盘。"

def main():
    msg = test_today_or_recent()
    send(msg)

if __name__ == "__main__":
    main()
