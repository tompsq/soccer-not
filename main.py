import os
import requests

# 1. 从环境变量读取密钥
K = os.environ.get("API_FOOTBALL_KEY")
T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")

def send(msg):
    """发送消息到 Telegram"""
    if not T or not C:
        print("【错误】未配置 TG_BOT_TOKEN 或 TG_CHAT_ID！")
        return
    url = f"https://api.telegram.org/bot{T}/sendMessage"
    res = requests.post(url, json={"chat_id": C, "text": msg})
    print(f"Telegram 发送响应状态: {res.status_code}")

def test_api():
    """验证 API-Football 密钥有效性与剩余额度"""
    if not K:
        return "【错误】未读取到 API_FOOTBALL_KEY 变量，请检查 Secrets 及 main.yml 配置。"
    
    # 直接在 URL 参数中附带 Key，避免 Header 格式差异导致的 403 鉴权失败
    url = f"https://v3.football.api-sports.io/status?key={K}"
    r = requests.get(url)
    
    if r.status_code != 200:
        return f"【API 报错】状态码: {r.status_code}\n{r.text}"
    
    data = r.json()
    account = data.get("response", {}).get("account", {})
    reqs = data.get("response", {}).get("requests", {})
    
    return (
        f"🎉【API 鉴权完全成功！】\n"
        f"用户: {account.get('firstname')} {account.get('lastname')}\n"
        f"今日已用请求数: {reqs.get('current')}/{reqs.get('limit_day')}"
    )

def get_fixtures():
    """抓取接下来 10 场赛事数据"""
    url = f"https://v3.football.api-sports.io/fixtures?next=10&key={K}"
    r = requests.get(url)
    if r.status_code != 200:
        return f"【赛事抓取失败】状态码: {r.status_code}\n{r.text}"
    
    data = r.json().get("response", [])
    if not data:
        return "【赛事推送】近期暂无最新赛事数据。"

    res = ["⚽【API-Football 热门赛事推送】"]
    for item in data:
        league_name = item.get("league", {}).get("name", "未知联赛")
        home = item.get("teams", {}).get("home", {}).get("name", "主队")
        away = item.get("teams", {}).get("away", {}).get("name", "客队")
        
        gh = item.get("goals", {}).get("home")
        ga = item.get("goals", {}).get("away")
        score_str = f"{gh} - {ga}" if gh is not None else "未开赛"
        
        res.append(f"• [{league_name}] {home} {score_str} {away}")
    
    return "\n".join(res)

if __name__ == "__main__":
    # 步骤 1: 验证 API 状态并发送通知
    status_msg = test_api()
    send(status_msg)
    
    # 步骤 2: 鉴权成功后抓取并推送赛事
    if "🎉" in status_msg:
        fixtures_msg = get_fixtures()
        send(fixtures_msg)
        
    print("程序运行结束。")
