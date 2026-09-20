import os, requests
from datetime import datetime, timezone, timedelta

API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY")
T, C = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")

def send(msg):
    if not T or not C: return
    url = f"https://api.telegram.org/bot{T}/sendMessage"
    requests.post(url, json={"chat_id": C, "text": msg})

def test_nations_league_odds():
    if not API_FOOTBALL_KEY:
        return "❌ 错误：未读取到 API_FOOTBALL_KEY！"
    
    headers = {"x-apisports-key": API_FOOTBALL_KEY}
    
    # 欧国联 ID 是 5，用 next=1 抓取接下来的一场国家队比赛，或者直接按日期查 2026-09-25 / 09-26
    url = "https://v3.football.api-sports.io/fixtures"
    params = {
        "league": 5,      # 欧国联 ID
        "season": 2026,
        "date": "2026-09-25" # 对应大马时间 09/26 02:45 (UTC时间是 09-25 18:45 左右)
    }
    
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        data = r.json()
        fixtures = data.get("response", [])
        
        if not fixtures:
            # 如果按具体日期没抓到，尝试用 next=1 看看欧国联最近的一场
            params = {"league": 5, "season": 2026, "next": 1}
            r = requests.get(url, headers=headers, params=params, timeout=10)
            fixtures = r.json().get("response", [])
            
        if not fixtures:
            return "⚽ 未能在 API 中找到欧国联近期赛事。"
        
        fix = fixtures[0]
        fixture_id = fix.get("fixture", {}).get("id")
        match_date = fix.get("fixture", {}).get("date")
        home = fix.get("teams", {}).get("home", {}).get("name")
        away = fix.get("teams", {}).get("away", {}).get("name")
        
        res = [
            "=====================",
            "🇪🇺 欧国联单场赛事与赔率测试",
            "=====================",
            f"🏟️ 对阵: {home} vs {away}",
            f"⏰ 时间(UTC): {match_date}",
            f"🆔 ID: {fixture_id}"
        ]
        
        # 请求赔率：亚盘、大小球、欧赔
        odds_url = "https://v3.football.api-sports.io/odds"
        o_res = requests.get(odds_url, headers=headers, params={"fixture": fixture_id}, timeout=5)
        
        if o_res.status_code == 200:
            odds_data = o_res.json().get("response", [])
            if odds_data:
                bookmakers = odds_data[0].get("bookmakers", [])
                if bookmakers:
                    bm = bookmakers[0]
                    res.append(f"🏢 机构: {bm.get('name')}")
                    
                    for bet in bm.get("bets", []):
                        b_name = bet.get("name")
                        values = bet.get("values", [])
                        
                        if b_name == "Match Winner": # 1X2 欧赔
                            o_str = " | ".join([f"{v.get('value')}: {v.get('odd')}" for v in values])
                            res.append(f"  - 欧赔 (1X2): {o_str}")
                        elif b_name == "Asian Handicap": # 亚盘
                            a_str = " | ".join([f"{v.get('value')} ({v.get('handicap', '')}): {v.get('odd')}" for v in values])
                            res.append(f"  - 亚盘: {a_str}")
                        elif "Goals Over/Under" in b_name: # 大小球
                            u_str = " | ".join([f"{v.get('value')} {v.get('handicap', '')}: {v.get('odd')}" for v in values])
                            res.append(f"  - 大小球: {u_str}")
                else:
                    res.append("  - 暂无开售赔率数据")
            else:
                res.append("  - 暂无赔率响应")
        
        res.append("-" * 21)
        return "\n".join(res)
        
    except Exception as e:
        return f"❌ 异常报错: {str(e)}"

def main():
    msg = test_nations_league_odds()
    send(msg)

if __name__ == "__main__":
    main()
