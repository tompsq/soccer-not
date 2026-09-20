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

def test_weekly_fixtures_and_odds():
    if not API_FOOTBALL_KEY:
        return "❌ 错误：未读取到 API_FOOTBALL_KEY！"
    
    headers = {
        "x-apisports-key": API_FOOTBALL_KEY
    }
    
    tz = timezone(timedelta(hours=8))
    today = datetime.now(tz)
    from_date = today.strftime("%Y-%m-%d")
    to_date = (today + timedelta(days=7)).strftime("%Y-%m-%d")
    
    # 1. 移除可能导致空的 season 参数，直接靠 from 和 to 抓取英超 (ID: 39)
    fixtures_url = "https://v3.football.api-sports.io/fixtures"
    params = {
        "league": 39,
        "from": from_date,
        "to": to_date
    }
    
    try:
        r = requests.get(fixtures_url, headers=headers, params=params, timeout=10)
        if r.status_code != 200:
            return f"❌ 获取赛程失败，状态码: {r.status_code}"
        
        data = r.json()
        fixtures = data.get("response", [])
        
        if not fixtures:
            return f"⚽ 英超在未来一周 ({from_date} 至 {to_date}) 暂无赛程安排。"
        
        res = [f"====================\n📅 英超未来一周赛程与赔率\n({from_date} ~ {to_date})\n===================="]
        
        for fix in fixtures[:3]: # 限制前3场测试
            fixture_id = fix.get("fixture", {}).get("id")
            match_date = fix.get("fixture", {}).get("date")
            home = fix.get("teams", {}).get("home", {}).get("name")
            away = fix.get("teams", {}).get("away", {}).get("name")
            
            match_block = [f"🏟️ {home} vs {away}\n⏰ 开赛: {match_date}"]
            
            # 2. 根据 fixture_id 请求赔率
            odds_url = "https://v3.football.api-sports.io/odds"
            odds_params = {
                "fixture": fixture_id
            }
            
            o_res = requests.get(odds_url, headers=headers, params=odds_params, timeout=5)
            if o_res.status_code == 200:
                odds_data = o_res.json().get("response", [])
                if odds_data:
                    bookmakers = odds_data[0].get("bookmakers", [])
                    if bookmakers:
                        bm = bookmakers[0]
                        for bet in bm.get("bets", []):
                            b_name = bet.get("name")
                            values = bet.get("values", [])
                            
                            if b_name == "Match Winner": # 欧赔
                                o_str = " | ".join([f"{v.get('value')}: {v.get('odd')}" for v in values])
                                match_block.append(f"  - 欧赔: {o_str}")
                            elif b_name == "Asian Handicap": # 亚盘
                                a_str = " | ".join([f"{v.get('value')} ({v.get('handicap', '')}): {v.get('odd')}" for v in values])
                                match_block.append(f"  - 亚盘: {a_str}")
                            elif "Goals Over/Under" in b_name: # 大小球
                                u_str = " | ".join([f"{v.get('value')} {v.get('handicap', '')}: {v.get('odd')}" for v in values])
                                match_block.append(f"  - 大小球: {u_str}")
                else:
                    match_block.append("  - 暂无开售赔率数据")
            
            res.append("\n".join(match_block) + "\n" + "-"*15)
            
        return "\n".join(res)
    except Exception as e:
        return f"❌ 异常报错: {str(e)}"

def main():
    msg = test_weekly_fixtures_and_odds()
    send(msg)

if __name__ == "__main__":
    main()
