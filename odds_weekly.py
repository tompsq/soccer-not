import os, requests

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

def test_next_match_odds():
    if not API_FOOTBALL_KEY:
        return "❌ 错误：未读取到 API_FOOTBALL_KEY！"
    
    headers = {"x-apisports-key": API_FOOTBALL_KEY}
    
    # 1. 使用 next=1 直接获取英超（ID: 39）接下来的最近 1 场比赛
    fixtures_url = "https://v3.football.api-sports.io/fixtures"
    params = {
        "league": 39,
        "season": 2026,
        "next": 1
    }
    
    try:
        r = requests.get(fixtures_url, headers=headers, params=params, timeout=10)
        if r.status_code != 200:
            return f"❌ 获取赛程失败，状态码: {r.status_code}"
        
        data = r.json()
        fixtures = data.get("response", [])
        
        if not fixtures:
            return f"⚽ 接口返回空：未找到英超下一场比赛数据。"
        
        fix = fixtures[0]
        fixture_id = fix.get("fixture", {}).get("id")
        match_date = fix.get("fixture", {}).get("date")
        home = fix.get("teams", {}).get("home", {}).get("name")
        away = fix.get("teams", {}).get("away", {}).get("name")
        
        res = [
            "=====================",
            "⚽ 英超下一场赛事赔率测试",
            "=====================",
            f"🏟️ 对阵: {home} vs {away}",
            f"⏰ 时间: {match_date}"
        ]
        
        # 2. 根据 fixture_id 请求赔率
        odds_url = "https://v3.football.api-sports.io/odds"
        odds_params = {"fixture": fixture_id}
        
        o_res = requests.get(odds_url, headers=headers, params=odds_params, timeout=5)
        if o_res.status_code == 200:
            odds_data = o_res.json().get("response", [])
            if odds_data:
                bookmakers = odds_data[0].get("bookmakers", [])
                if bookmakers:
                    bm = bookmakers[0]
                    bm_name = bm.get("name", "主流机构")
                    res.append(f"🏢 机构: {bm_name}")
                    
                    for bet in bm.get("bets", []):
                        b_name = bet.get("name")
                        values = bet.get("values", [])
                        
                        if b_name == "Match Winner": # 欧赔
                            o_str = " | ".join([f"{v.get('value')}: {v.get('odd')}" for v in values])
                            res.append(f"  - 欧赔: {o_str}")
                        elif b_name == "Asian Handicap": # 亚盘
                            a_str = " | ".join([f"{v.get('value')} ({v.get('handicap', '')}): {v.get('odd')}" for v in values])
                            res.append(f"  - 亚盘: {a_str}")
                        elif "Goals Over/Under" in b_name: # 大小球
                            u_str = " | ".join([f"{v.get('value')} {v.get('handicap', '')}: {v.get('odd')}" for v in values])
                            res.append(f"  - 大小球: {u_str}")
                else:
                    res.append("  - 暂无开售赔率数据（可能开赛前几天才开盘）")
            else:
                res.append("  - 暂无赔率响应数据")
        else:
            res.append(f"  - 赔率接口请求失败: {o_res.status_code}")
            
        res.append("-" * 21)
        return "\n".join(res)
        
    except Exception as e:
        return f"❌ 异常报错: {str(e)}"

def main():
    msg = test_next_match_odds()
    send(msg)

if __name__ == "__main__":
    main()
