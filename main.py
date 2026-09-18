import os
import requests
from datetime import datetime, timedelta

K = os.environ.get("API_FOOTBALL_KEY")
T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")

HEADERS = {
    "x-apisports-key": K
}

# 关注的联赛 ID
LEAGUES = {
    "英超": 39,
    "西甲": 140,
    "意甲": 135,
    "德甲": 78,
    "法甲": 61,
    "欧冠": 2
}

def send(msg):
    if not T or not C:
        return
    url = f"https://api.telegram.org/bot{T}/sendMessage"
    
    if len(msg) > 3800:
        lines, cur = msg.split("\n"), ""
        for line in lines:
            if len(cur) + len(line) + 1 > 3800:
                requests.post(url, json={"chat_id": C, "text": cur})
                cur = line
            else:
                cur = (cur + "\n" + line) if cur else line
        if cur:
            requests.post(url, json={"chat_id": C, "text": cur})
    else:
        requests.post(url, json={"chat_id": C, "text": msg})

def get_league_fixtures():
    # 查询从今天开始未来 7 天内的比赛
    today = datetime.now()
    from_date = today.strftime("%Y-%m-%d")
    to_date = (today + timedelta(days=7)).strftime("%Y-%m-%d")
    
    res = [f"⚽【各大联赛赛程推送 ({from_date} ~ {to_date})】"]
    
    for name, lid in LEAGUES.items():
        # 通过日期范围查询，兼容性最好
        url = f"https://v3.football.api-sports.io/fixtures?league={lid}&from={from_date}&to={to_date}"
        r = requests.get(url, headers=HEADERS)
        if r.status_code != 200:
            continue
            
        data = r.json().get("response", [])
        if not data:
            continue
            
        match_list = []
        for item in data[:5]:  # 只取前 5 场
            home = item["teams"]["home"]["name"]
            away = item["teams"]["away"]["name"]
            status = item["fixture"]["status"]["short"]
            match_date = item["fixture"]["date"][:10]
            
            gh = item["goals"]["home"]
            ga = item["goals"]["away"]
            score = f"{gh}-{ga}" if gh is not None else "未开赛"
            
            match_list.append(f"• [{match_date}] {home} {score} {away} ({status})")
            
        if match_list:
            res.append(f"\n🏆 {name}")
            res.extend(match_list)
            
    if len(res) == 1:
        return f"⚽【赛事推送】未来 7 天内无相关联赛比赛，或今日 API 请求次数已耗尽。"
        
    return "\n".join(res)

if __name__ == "__main__":
    msg = get_league_fixtures()
    send(msg)
    print("推送完成！")
