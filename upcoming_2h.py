import os, requests
from datetime import datetime, timezone, timedelta

T, C = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")

# 11大核心联赛在 ESPN 上的公开代号
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
    tz = timezone(timedelta(hours=8))
    today = datetime.now(tz)
    
    # 强制覆盖过去 3 天（今天、昨天、前天，即周五、周六、周日），确保周六的比赛不漏掉
    date_strings = [(today - timedelta(days=i)).strftime("%Y%m%d") for i in range(3)]
    
    league_results = {}
    
    for league_code, league_name in LEAGUES_ESPN.items():
        league_matches = set()
        for d_str in date_strings:
            try:
                # 显式带上 dates 参数，才能拿到指定日期的历史赛果
                url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/scoreboard?dates={d_str}"
                r = requests.get(url, timeout=5)
                if r.status_code != 200:
                    continue
                
                data = r.json()
                events = data.get("events", [])

                for ev in events:
                    status_type = ev.get("status", {}).get("type", {})
                    is_completed = status_type.get("completed", False)
                    
                    # 只要已经完场
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
                            match_str = f"{home_team} {home_score} - {away_score} {away_team}"
                            league_matches.add(match_str)
            except Exception as e:
                continue
                
        if league_matches:
            league_results[league_name] = list(league_matches)

    if not league_results:
        return "⚽ 近期暂无已完场比赛记录。"

    for l_name, matches in league_results.items():
        res.append(f"【{l_name}】\n" + "\n".join(matches) + "\n" + "-"*15)
        
    return "\n".join(res)

def main():
    msg = get_free_scores()
    send(msg)

if __name__ == "__main__":
    main()
