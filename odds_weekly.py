import os, requests

API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY")
T, C = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")

def send(msg):
    if not T or not C: return
    url = f"https://api.telegram.org/bot{T}/sendMessage"
    requests.post(url, json={"chat_id": C, "text": msg})

def test_single_match_only():
    if not API_FOOTBALL_KEY:
        return "❌ 错误：未读取到 API_FOOTBALL_KEY！"
    
    headers = {"x-apisports-key": API_FOOTBALL_KEY}
    
    # 不设日期限制，直接用 next=1 抓取英超最近的 1 场比赛
    url = "https://v3.football.api-sports.io/fixtures"
    params = {
        "league": 39,
        "season": 2026,
        "next": 1
    }
    
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        if r.status_code != 200:
            return f"❌ 接口请求失败，状态码: {r.status_code}"
        
        data = r.json()
        fixtures = data.get("response", [])
        
        if not fixtures:
            return "⚽ 目前 API 数据库中暂无英超下一场比赛（可能处于间歇期远期无数据）。"
        
        # 严格只取单场
        fix = fixtures[0]
        fixture_id = fix.get("fixture", {}).get("id")
        match_date = fix.get("fixture", {}).get("date")
        home = fix.get("teams", {}).get("home", {}).get("name")
        away = fix.get("teams", {}).get("away", {}).get("name")
        
        res = [
            "=====================",
            "⚽ 英超单场赛事测试",
            "=====================",
            f"🏟️ 对阵: {home} vs {away}",
            f"⏰ 时间: {match_date}",
            f"🆔 ID: {fixture_id}"
        ]
        
        # 顺便尝试请求该单场的赔率
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
                        if bet.get("name") == "Match Winner":
                            o_str = " | ".join([f"{v.get('value')}: {v.get('odd')}" for v in bet.get("values", [])])
                            res.append(f"  - 欧赔: {o_str}")
                else:
                    res.append("  - 暂无开售赔率数据")
            else:
                res.append("  - 暂无赔率响应")
        
        res.append("-" * 21)
        return "\n".join(res)
        
    except Exception as e:
        return f"❌ 异常报错: {str(e)}"

def main():
    msg = test_single_match_only()
    send(msg)

if __name__ == "__main__":
    main()
