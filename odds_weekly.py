import os, requests

API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY")
T, C = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")

def send(msg):
    if not T or not C: return
    url = f"https://api.telegram.org/bot{T}/sendMessage"
    requests.post(url, json={"chat_id": C, "text": msg})

def test_exact_date_odds():
    if not API_FOOTBALL_KEY:
        return "❌ 错误：未读取到 API_FOOTBALL_KEY！"
    
    headers = {"x-apisports-key": API_FOOTBALL_KEY}
    
    # 直接精准锁定 2026-10-10 这一天查英超(39)
    url = "https://v3.football.api-sports.io/fixtures"
    params = {
        "league": 39,
        "season": 2026,
        "date": "2026-10-10"
    }
    
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        if r.status_code != 200:
            return f"❌ 接口请求失败，状态码: {r.status_code}, 响应: {r.text}"
        
        data = r.json()
        fixtures = data.get("response", [])
        
        if not fixtures:
            return f"❌ 状态码200，但 date=2026-10-10 返回空数据。说明 API-Football 当前数据库里还没有录入这天的比赛，或者该 Key 的订阅套餐不包含未来赛程权限。"
        
        # 抓到了就取第一场测试赔率
        fix = fixtures[0]
        fixture_id = fix.get("fixture", {}).get("id")
        home = fix.get("teams", {}).get("home", {}).get("name")
        away = fix.get("teams", {}).get("away", {}).get("name")
        
        res = [f"✅ 成功命中 10/10 赛事：{home} vs {away} (ID: {fixture_id})"]
        
        # 拉取赔率
        odds_url = "https://v3.football.api-sports.io/odds"
        o_res = requests.get(odds_url, headers=headers, params={"fixture": fixture_id}, timeout=5)
        
        if o_res.status_code == 200:
            odds_data = o_res.json().get("response", [])
            if odds_data:
                bm = odds_data[0].get("bookmakers", [])[0]
                res.append(f"🏢 机构: {bm.get('name')}")
                for bet in bm.get("bets", []):
                    if bet.get("name") == "Match Winner":
                        o_str = " | ".join([f"{v.get('value')}: {v.get('odd')}" for v in bet.get("values", [])])
                        res.append(f"  - 欧赔: {o_str}")
            else:
                res.append("  - 赛事存在，但该场比赛尚无赔率数据")
        else:
            res.append(f"  - 赔率请求失败: {o_res.status_code}")
            
        return "\n".join(res)
    except Exception as e:
        return f"❌ 异常报错: {str(e)}"

def main():
    msg = test_exact_date_odds()
    send(msg)

if __name__ == "__main__":
    main()
