import os, requests
from datetime import datetime, timezone, timedelta

T, C = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")

# 11 个核心联赛的目标关键字
TARGET_LEAGUES = {
    "Premier League": "英超",
    "La Liga": "西甲",
    "Serie A": "意甲",
    "Bundesliga": "德甲",
    "Ligue 1": "法甲",
    "Champions League": "欧冠",
    "Europa League": "欧联/欧协联",
    "Conference League": "欧联/欧协联",
    "Primeira Liga": "葡超",
    "Premiership": "苏超",
    "Pro League": "比甲",
    "Super League": "希超"
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
        tz = timezone(timedelta(hours=8))
        today = datetime.now(tz)
        
        league_results = {}
        found_leagues = set() # 用来记录接口返回了哪些联赛名字，方便排查
        
        # 连查最近 3 天（今天、昨天、前天），确保周末的比赛绝对能抓到
        for i in range(3):
            target_date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            url = f"https://www.thesportsdb.com/api/v1/json/3/eventsday.php?d={target_date}&s=Soccer"
            r = requests.get(url, timeout=10)
            data = r.json()
            events = data.get("events")
            
            if not events: continue
            
            for ev in events:
                league_raw = ev.get("strLeague", "")
                found_leagues.add(league_raw)
                
                matched_name = None
                for key, val in TARGET_LEAGUES.items():
                    if key.lower() in league_raw.lower():
                        matched_name = val
                        break
                
                if not matched_name: continue

                home = ev.get("strHomeTeam", "")
                away = ev.get("strAwayTeam", "")
                h_score = ev.get("intHomeScore", "-")
                a_score = ev.get("intAwayScore", "-")
                status = ev.get("strStatus", "")
                
                # 筛选已完场
                if status in ["FT", "AET", "Pen", "Finished"] or (h_score is not None and h_score != "None" and h_score != ""):
                    match_str = f"{home} {h_score} - {a_score} {away}"
                    if match_str not in league_results.get(matched_name, []):
                        league_results.setdefault(matched_name, []).append(match_str)

        if not league_results:
            # 如果还是空的，把接口里读到的所有联赛名字打印出来排查
            debug_str = "\n".join(list(found_leagues)[:10]) if found_leagues else "无数据"
            return f"⚽ 暂无这 11 个联赛的完场记录。\n[调试] 接口返回的联赛有：\n{debug_str}"

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
