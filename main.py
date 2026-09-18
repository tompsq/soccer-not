import os, requests

K = os.environ.get("API_FOOTBALL_KEY")
T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")

HEADERS = {
    "x-apisports-key": K,
    "x-rapidapi-key": K
}

def send(msg):
    u = f"https://api.telegram.org/bot{T}/sendMessage"
    res = requests.post(u, json={"chat_id": C, "text": msg})
    print(f"TG响应状态: {res.status_code}")

def get_fixtures():
    # 抓取接下来最即时的 10 场赛事（全联赛通用）
    url = "https://v3.football.api-sports.io/fixtures?next=10"
    r = requests.get(url, headers=HEADERS)
    
    if r.status_code != 200:
        return f"【API报错】状态码: {r.status_code}\n{r.text}"
    
    data = r.json().get("response", [])
    if not data:
        return "【赛事推送】今日暂无最新赛事。"

    res = ["【API-Football 热门赛事推送】"]
    for item in data:
        league_name = item.get("league", {}).get("name", "未知联赛")
        home = item.get("teams", {}).get("home", {}).get("name", "主队")
        away = item.get("teams", {}).get("away", {}).get("name", "客队")
        status = item.get("fixture", {}).get("status", {}).get("short", "NS")
        
        # 比分解析
        gh = item.get("goals", {}).get("home")
        ga = item.get("goals", {}).get("away")
        score_str = f"{gh} - {ga}" if gh is not None else "未开赛"
        
        res.append(f"[{league_name}] {home} {score_str} {away} ({status})")
    
    return "\n".join(res)

if __name__ == "__main__":
    msg = get_fixtures()
    send(msg)
    print("推送完成")
