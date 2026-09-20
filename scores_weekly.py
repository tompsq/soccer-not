import os, requests
from datetime import datetime, timezone, timedelta

T, C = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")

# 严格锁定我们要的 11 个联赛名称关键字（对应公开接口中的联赛名称）
TARGET_LEAGUES = {
    "English Premier League": "英超",
    "Spanish La Liga": "西甲",
    "Italian Serie A": "意甲",
    "German Bundesliga": "德甲",
    "French Ligue 1": "法甲",
    "UEFA Champions League": "欧冠",
    "UEFA Europa League": "欧联/欧协联",
    "UEFA Europa Conference League": "欧联/欧协联",
    "Portuguese Primeira Liga": "葡超",
    "Scottish Premiership": "苏超",
    "Belgian Pro League": "比甲",
    "Greek Super League": "希超"
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
    try:
        # 获取昨天和前天的完场数据，确保周二能查到周末的比赛
        tz = timezone(timedelta(hours=8))
        yesterday = (datetime.now(tz) - timedelta(days=1)).strftime("%Y-%m-%d")
        
        url = f"https://www.thesportsdb.com/api/v1/json/3/eventsday.php?d={yesterday}&s=Soccer"
        r = requests.get(url, timeout=10)
        data = r.json()
        
        events = data.get("events")
        if not events:
            return "⚽ 暂无符合条件的完场足球比赛记录。"
        
        league_results = {}
        for ev in events:
            league_raw = ev.get("strLeague", "")
            
            # 严格匹配我们需要的 11 个联赛
            matched_name = None
            for key, val in TARGET_LEAGUES.items():
                if key.lower() in league_raw.lower():
                    matched_name = val
                    break
            
            if not matched_name:
                continue # 不是我们要的 11 个联赛直接跳过！

            home = ev.get("strHomeTeam", "")
            away = ev.get("strAwayTeam", "")
            h_score = ev.get("intHomeScore", "-")
            a_score = ev.get("intAwayScore", "-")
            status = ev.get("strStatus", "")
            
            # 筛选已完场
            if status in ["FT", "AET", "Pen", "Finished"] or (h_score is not None and h_score != "None" and h_score != ""):
                league_results.setdefault(matched_name, []).append(f"{home} {h_score} - {a_score} {away}")

        if not league_results:
            return "⚽ 上周末这 11 个联赛暂无已完场比赛记录。"

        res = ["====================\n⚽ 11大核心联赛完场比分 (白嫖版)\n===================="]
        for l_name, matches in league_results.items():
            res.append(f"【{l_name}】\n" + "\n".join(matches) + "\n" + "-"*15)
            
        return "\n".join(res)
    except Exception as e:
        return f"❌ 获取比分异常：{str(e)}"

def main():
    msg = get_free_scores()
    send(msg)

if __name__ == "__main__":
    main()
