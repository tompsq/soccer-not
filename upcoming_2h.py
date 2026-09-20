import os, requests
from datetime import datetime, timezone, timedelta

T, C = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")

# 11大联赛在 ESPN 上的公开代码
LEAGUES_ESPN = {
    "eng.1": "英超",
    "esp.1": "西甲",
    "ita.1": "意甲",
    "ger.1": "德甲",
    "fra.1": "法甲",
    "uefa.champions": "欧冠",
    "por.1": "葡超",
    "sco.1": "苏超",
    "bel.1": "比甲",
    "gre.1": "希超"
}

def send(msg):
    if not T or not C: return
    url = f"https://api.telegram.org/bot{T}/sendMessage"
    if len(msg) > 3800:
        for i in range(0, len(msg), 3800):
            requests.post(url, json={"chat_id": C, "text": msg[i:i+3800]})
    else:
        requests.post(url, json={"chat_id": C, "text": msg})

def get_free_scores():
    res = ["====================\n⚽ 11大核心联赛完场比分 (白嫖版)\n===================="]
    has_data = False
    
    tz = timezone(timedelta(hours=8))
    # 我们可以通过 dates 参数指定查最近几天（例如格式为 20260918-20260920 的过去周末）
    today = datetime.now(tz)
    d_start = (today - timedelta(days=3)).strftime("%Y%m%d")
    d_end = today.strftime("%Y%m%d")

    for league_code, league_name in LEAGUES_ESPN.items():
        try:
            # 加上 dates 参数强制拉取过去几天的比赛
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/scoreboard?dates={d_start}-{d_end}"
            r = requests.get(url, timeout=5)
            if r.status_code != 200:
                continue
            
            data = r.json()
            events = data.get("events", [])
            league_matches = []

            for ev in events:
                status_type = ev.get("status", {}).get("type", {})
                is_completed = status_type.get("completed", False)
                
                if is_completed:
                    competitions = ev.get("competitions", [{}])[0]
                    competitors = competitions.get("competitors", [])
                    
                    home_team, home_score = "", "-"
                    away_team, away_score = "", "-"
                    
                    for comp in competitors:
                        if comp.get("homeAway") == "home":
                            home_team = comp.get("team", {}).get("displayName", "")
                            home_score = comp.get("score", "0")
                        elif comp.get("homeAway") == "away":
                            away_team = comp.get("team", {}).get("displayName", "")
                            away_score = comp.get("score", "0")
                    
                    if home_team and away_team:
                        league_matches.append(f"{home_team} {home_score} - {away_score} {away_team}")

            if league_matches:
                has_data = True
                res.append(f"【{league_name}】\n" + "\n".join(league_matches) + "\n" + "-"*15)
                
        except Exception as e:
            print(f"Error {league_code}: {e}")
            continue

    if not has_data:
        return f"⚽ 检索区间 ({d_start}至{d_end}) 内这 11 个联赛暂无已完场比赛记录。"
        
    return "\n".join(res)

def main():
    msg = get_free_scores()
    send(msg)

if __name__ == "__main__":
    main()
