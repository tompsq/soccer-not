import os, requests

API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY")
T, C = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")

def send(msg):
    if not T or not C: return
    url = f"https://api.telegram.org/bot{T}/sendMessage"
    requests.post(url, json={"chat_id": C, "text": msg})

def debug_check():
    if not API_FOOTBALL_KEY:
        return "❌ 错误：未读取到 API_FOOTBALL_KEY！"
    
    headers = {"x-apisports-key": API_FOOTBALL_KEY}
    
    # 1. 尝试直接搜当前日期的所有比赛（不限联赛，看看今天有没有球赛）
    url = "https://v3.football.api-sports.io/fixtures"
    params = {"date": "2026-09-25"} # 对应你截图里的日期
    
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        data = r.json()
        fixtures = data.get("response", [])
        
        if fixtures:
            res = [f"✅ 成功！2026-09-25 当天共有 {len(fixtures)} 场比赛，前3场为："]
            for fix in fixtures[:3]:
                league = fix.get("league", {}).get("name")
                home = fix.get("teams", {}).get("home", {}).get("name")
                away = fix.get("teams", {}).get("away", {}).get("name")
                res.append(f"[{league}] {home} vs {away}")
            return "\n".join(res)
        else:
            return "❌ 2026-09-25 传日期查出来是空！说明参数或日期格式需要调整。"
            
    except Exception as e:
        return f"❌ 异常报错: {str(e)}"

def main():
    msg = debug_check()
    send(msg)

if __name__ == "__main__":
    main()
