import os, requests

K = os.environ.get("API_FOOTBALL_KEY")
T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")

def send(msg):
    u = f"https://api.telegram.org/bot{T}/sendMessage"
    res = requests.post(u, json={"chat_id": C, "text": msg})
    print(f"TG响应状态: {res.status_code}")

def test_api():
    if not K:
        return "【错误】未读取到 API_FOOTBALL_KEY 变量，请检查 Secrets 配置。"
    
    # 直接将 Key 作为 URL 参数传递，100% 避开 Header 识别失败问题
    url = f"https://v3.football.api-sports.io/status?key={K}"
    r = requests.get(url)
    
    if r.status_code != 200:
        return f"【API报错】状态码: {r.status_code}\n{r.text}"
    
    data = r.json()
    account = data.get("response", {}).get("account", {})
    reqs = data.get("response", {}).get("requests", {})
    
    return (
        f"🎉【API 鉴权完全成功！】\n"
        f"用户: {account.get('firstname')} {account.get('lastname')}\n"
        f"今日已用请求: {reqs.get('current')}/{reqs.get('limit_day')}"
    )

def get_fixtures():
    # 抓取接下来 10 场热门比赛
    url = f"https://v3.football.api-sports.io/fixtures?next=10&key={K}"
    r = requests.get(url)
    if r.status_code != 200:
        return f"【赛事抓取失败】状态码: {r.status_code}\n{r.text}"
    
    data = r.json().get("response", [])
    if not data:
        return "【赛事推送】今日暂无最新赛事数据。"

    res = ["【API-Football 热门赛事推送】"]
    for item in data:
        league_name = item.get("league", {}).get("name", "未知联赛")
        home = item.get("teams", {}).get("home", {}).get("name", "主队")
        away = item.get("teams", {}).get("away", {}).get("name", "客队")
        
        gh = item.get("goals", {}).get("home")
        ga = item.get("goals", {}).get("away")
        score_str = f"{gh} - {ga}" if gh is not None else "未开赛"
        
        res.append(f"[{league_name}] {home} {score_str} {away}")
    
    return "\n".join(res)

if __name__ == "__main__":
    # 先验证 Key，再发送比赛
    status_msg = test_api()
    send(status_msg)
    
    if "🎉" in status_msg:
        fixtures_msg = get_fixtures()
        send(fixtures_msg)
        
    print("运行完成")
