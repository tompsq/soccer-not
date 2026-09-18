import os
import requests
from datetime import datetime

K = os.environ.get("API_FOOTBALL_KEY")
T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")

HEADERS = {
    "x-apisports-key": K
}

# 五大联赛 + 欧冠的 League ID
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

def get_current_season():
    # 欧洲联赛跨年（如 2026-2027 赛季），8月前属于前一年的赛季
    now = datetime.now()
    return now.year if now.month >= 8 else now.year - 1

def get_league_fixtures():
    season = get_current_season()
    res = ["⚽【各大联赛最新赛程与完场比分】"]
    
    for name, lid in LEAGUES.items():
        # 必须同时带上 season 参数
        url = f"https://v3.football.api-sports.io/fixtures?league={lid}&season={season}&next=5"
        r = requests.get(url, headers=HEADERS)
        if r.status_code != 200:
            continue
            
        data = r.json().get("response", [])
        if not data:
            continue
            
        match_list = []
        for item in data:
            home = item["teams"]["home"]["name"]
            away = item["teams"]["away"]["name"]
            status = item["fixture"]["status"]["short"]
            
            gh = item["goals"]["home"]
            ga = item["goals"]["away"]
            score = f"{gh}-{ga}" if gh is not None else "未开赛"
            
            match_list.append(f"• {home} {score} {away} ({status})")
            
        if match_list:
            res.append(f"\n🏆 {name}")
            res.extend(match_list)
            
    if len(res) == 1:
        return "⚽【赛事推送】暂未获取到近期赛事，请检查 API 额度或赛季设置。"
        
    return "\n".join(res)

if __name__ == "__main__":
    msg = get_league_fixtures()
    send(msg)
    print("推送完成！")
