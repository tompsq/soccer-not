import os, requests
from datetime import datetime, timezone, timedelta

API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY")
T, C = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")

def send(msg):
    if not T or not C: return
    url = f"https://api.telegram.org/bot{T}/sendMessage"
    if len(msg) > 3800:
        for i in range(0, len(msg), 3800):
            requests.post(url, json={"chat_id": C, "text": msg[i:i+3800]})
    else:
        requests.post(url, json={"chat_id": C, "text": msg})

def test_debug_fixtures():
    if not API_FOOTBALL_KEY:
        return "❌ 错误：未读取到 API_FOOTBALL_KEY！"
    
    headers = {"x-apisports-key": API_FOOTBALL_KEY}
    
    tz = timezone(timedelta(hours=8))
    today = datetime.now(tz)
    
    # 扩大范围：查未来 30 天，看看最近的比赛在哪一天
    from_date = today.strftime("%Y-%m-%d")
    to_date = (today + timedelta(days=30)).strftime("%Y-%m-%d")
    
    fixtures_url = "https://v3.football.api-sports.io/fixtures"
    params = {
        "league": 39, # 英超
        "from": from_date,
        "to": to_date
    }
    
    try:
        r = requests.get(fixtures_url, headers=headers, params=params, timeout=10)
        data = r.json()
        fixtures = data.get("response", [])
        
        if not fixtures:
            # 如果未来30天都没有，顺便查一下当前的赛季年份配置对不对
            return f"⚽ 经检测：英超在未来 30 天 ({from_date} 至 {to_date}) 均无赛程。当前可能处于国家队比赛周或休赛期！"
        
        res = [f"====================\n⚽ 英超近期赛程探测 (未来30天)\n===================="]
        
        # 打印前 3 场查到的比赛
        for fix in fixtures[:3]:
            match_date = fix.get("fixture", {}).get("date")
            home = fix.get("teams", {}).get("home", {}).get("name")
            away = fix.get("teams", {}).get("away", {}).get("name")
            res.append(f"🏟️ {home} vs {away}\n⏰ {match_date}")
            
        return "\n".join(res)
    except Exception as e:
        return f"❌ 异常报错: {str(e)}"

def main():
    msg = test_debug_fixtures()
    send(msg)

if __name__ == "__main__":
    main()
