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
    39: "英超",
    140: "西甲",
    135: "意甲",
    78: "德甲",
    61: "法甲",
    2: "欧冠"
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

def get_fixtures_by_date(target_date):
    # API-Sports 最通用的日期查比赛接口
    url = f"https://v3.football.api-sports.io/fixtures?date={target_date}"
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200:
        return None, f"【API 请求失败】状态码: {r.status_code}"
    
    data = r.json()
    errors = data.get("errors", {})
    if errors:
        return None, f"【API 返回错误】{errors}"
        
    return data.get("response", []), None

def main():
    today = datetime.now()
    # 查找今天和明天的比赛（只需调用两次 API，大幅节省额度）
    dates_to_check = [
        today.strftime("%Y-%m-%d"),
        (today + timedelta(days=1)).strftime("%Y-%m-%d")
    ]
    
    res = ["⚽【热门足球联赛赛程与比分推送】"]
    has_match = False
    
    for d in dates_to_check:
        fixtures, err = get_fixtures_by_date(d)
        if err:
            send(err)
            return
            
        day_matches = {}
        for item in fixtures:
            lid = item.get("league", {}).get("id")
            if lid in LEAGUES:
                league_name = LEAGUES[lid]
                home = item["teams"]["home"]["name"]
                away = item["teams"]["away"]["name"]
                status = item["fixture"]["status"]["short"]
                
                gh = item["goals"]["home"]
                ga = item["goals"]["away"]
                score = f"{gh}-{ga}" if gh is not None else "未开赛"
                
                match_str = f"• {home} {score} {away} ({status})"
                if league_name not in day_matches:
                    day_matches[league_name] = []
                day_matches[league_name].append(match_str)
                has_match = True
                
        if day_matches:
            res.append(f"\n📅 **日期: {d}**")
            for lname, m_list in day_matches.items():
                res.append(f"🏆 {lname}")
                res.extend(m_list)
                
    if not has_match:
        res.append("\n今明两天暂无关注联赛的比赛安排。")
        
    send("\n".join(res))

if __name__ == "__main__":
    main()
    print("推送程序执行完毕！")
