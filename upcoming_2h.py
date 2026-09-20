import os, requests
from datetime import datetime, timezone, timedelta

T, C = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")

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
        # 使用另一个更全的开源免费足球数据源 (openfootball / football-data 聚合源)
        # 获取当前赛季最新的比赛结果
        url = "https://raw.githubusercontent.com/openfootball/football.json/master/2026/en.1.json" # 以英超为例测试开源数据
        
        # 为了更稳妥，我们直接请求一个聚合了欧洲五大联赛近期比分的稳定公开 API
        r = requests.get("https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard", timeout=10)
        data = r.json()
        
        events = data.get("events", [])
        if not events:
            return "⚽ 近期暂无英超完场比赛记录。"
            
        res = ["====================\n⚽ 欧洲主流联赛完场比分 (白嫖版)\n===================="]
        match_list = []
        
        for ev in events:
            status = ev.get("status", {}).get("type", {}).get("completed", False)
            if status: # 已完场
                name = ev.get("name", "") # 例如 "Arsenal vs. Chelsea"
                competitions = ev.get("competitions", [{}])[0]
                competitors = competitions.get("competitors", [])
                
                home_team, home_score = "", ""
                away_team, away_score = "", ""
                
                for comp in competitors:
                    if comp.get("homeAway") == "home":
                        home_team = comp.get("team", {}).get("displayName", "")
                        home_score = comp.get("score", "")
                    elif comp.get("homeAway") == "away":
                        away_team = comp.get("team", {}).get("displayName", "")
                        away_score = comp.get("score", "")
                
                if home_team and away_team:
                    match_list.append(f"{home_team} {home_score} - {away_score} {away_team}")
                    
        if match_list:
            res.append("【英超】\n" + "\n".join(match_list) + "\n" + "-"*15)
        else:
            res.append("【英超】近期暂无完场比赛。")
            
        return "\n".join(res)
    except Exception as e:
        return f"❌ 获取比分异常：{str(e)}"

def main():
    msg = get_free_scores()
    send(msg)

if __name__ == "__main__":
    main()
