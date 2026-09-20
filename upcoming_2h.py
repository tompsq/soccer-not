import os, requests
from datetime import datetime, timezone, timedelta

T, C = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")

# 11大联赛在 ESPN 上的免费公开代号映射
LEAGUES_ESPN = {
    "eng.1": "英超",
    "esp.1": "西甲",
    "ita.1": "意甲",
    "ger.1": "德甲",
    "fra.1": "法甲",
    "uefa.champions": "欧冠",
    "uefa.europa": "欧联/欧协联",
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

    for league_code, league_name in LEAGUES_ESPN.items():
        try:
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/scoreboard"
            r = requests.get(url, timeout=5)
            if r.status_code != 200:
                continue
            
            data = r.json()
            events = data.get("events", [])
            league_matches = []

            for ev in events:
                status_type = ev.get("status", {}).get("type", {})
                is_completed = status_type.get("completed", False)
                
                # 如果比赛已经完场
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
            print(f"Error fetching {league_code}: {e}")
            continue

    if not has_data:
        return "⚽ 近期（周末/近期赛程）这 11 个联赛暂无已完场比赛记录。"
        
    return "\n".join(res)

def main():
    msg = get_free_scores()
    send(msg)

if __name__ == "__main__":
    main()
