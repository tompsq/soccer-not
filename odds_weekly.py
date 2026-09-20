import os, requests

API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY")
T, C = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")

def send(msg):
    if not T or not C: return
    url = f"https://api.telegram.org/bot{T}/sendMessage"
    if len(msg) > 3800:
        msg = msg[:3800]
    requests.post(url, json={"chat_id": C, "text": msg})

def debug_raw_response():
    if not API_FOOTBALL_KEY:
        return "❌ 错误：未读取到 API_FOOTBALL_KEY！"
    
    headers = {"x-apisports-key": API_FOOTBALL_KEY}
    
    # 尝试不加任何过滤，直接查英超，看 API 到底吐出什么（或者有没有错误提示）
    url = "https://v3.football.api-sports.io/fixtures"
    params = {"league": 39, "season": 2026, "last": 5} # 查最近已结束的 5 场
    
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        data = r.json()
        
        # 检查是否有 API 官方的错误提示
        errors = data.get("errors", {})
        if errors:
            return f"❌ API 明确报错: {str(errors)}"
            
        fixtures = data.get("response", [])
        if fixtures:
            fix = fixtures[0]
            home = fix.get("teams", {}).get("home", {}).get("name")
            away = fix.get("teams", {}).get("away", {}).get("name")
            return f"✅ API 通信正常！查到最近完场比赛：{home} vs {away}"
        else:
            return f"⚠️ 状态码 200 但 response 为空。完整响应: {str(data)[:200]}"
            
    except Exception as e:
        return f"❌ 异常报错: {str(e)}"

def main():
    msg = debug_raw_response()
    send(msg)

if __name__ == "__main__":
    main()
