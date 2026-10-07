import os
import requests
import pandas as pd
from datetime import datetime

# 使用公开的英超及主流联赛实时 JSON 数据源
LEAGUES_DATA = {
    "Premier League": "https://footballraw.github.io/football-api/2025-26/england-premier-league.json",
    "La Liga": "https://footballraw.github.io/football-api/2025-26/spain-la-liga.json",
    "Serie A": "https://footballraw.github.io/football-api/2025-26/italy-serie-a.json",
    "Bundesliga": "https://footballraw.github.io/football-api/2025-26/germany-bundesliga.json",
    "Ligue 1": "https://footballraw.github.io/football-api/2025-26/france-ligue-1.json"
}

TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")

def send_telegram_document(filepath, caption):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        print("未检测到 Telegram 环境变量，跳过发送。")
        return
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendDocument"
    try:
        with open(filepath, 'rb') as f:
            files = {'document': f}
            data = {'chat_id': TG_CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}
            resp = requests.post(url, data=data, files=files)
            if resp.status_code == 200:
                print("✅ 足球赛事数据报表已成功发送到 Telegram！")
            else:
                print(f"❌ 发送失败: {resp.text}")
    except Exception as e:
        print(f"TG 发送异常: {e}")

def fetch_data(league_name, url):
    print(f"正在获取 {league_name} 数据...")
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            print(f"⚠️ {league_name} 链接返回状态码: {resp.status_code}")
            return []
        
        data = resp.json()
        teams_stats = {}
        
        matches = data.get("matches", data.get("games", []))
        for m in matches:
            score = m.get("score", {})
            ft = score.get("ft")
            if not ft or len(ft) < 2:
                continue
                
            team1 = m.get("team1", m.get("homeTeam"))
            team2 = m.get("team2", m.get("awayTeam"))
            if not team1 or not team2:
                continue
                
            goals1, goals2 = ft[0], ft[1]
            
            for t in [team1, team2]:
                if t not in teams_stats:
                    teams_stats[t] = {"Matches": 0, "Points": 0, "Goals For": 0, "Goals Against": 0}
            
            teams_stats[team1]["Matches"] += 1
            teams_stats[team2]["Matches"] += 1
            teams_stats[team1]["Goals For"] += goals1
            teams_stats[team1]["Goals Against"] += goals2
            teams_stats[team2]["Goals For"] += goals2
            teams_stats[team2]["Goals Against"] += goals1
            
            if goals1 > goals2:
                teams_stats[team1]["Points"] += 3
            elif goals1 < goals2:
                teams_stats[team2]["Points"] += 3
            else:
                teams_stats[team1]["Points"] += 1
                teams_stats[team2]["Points"] += 1
                
        rows = []
        for team, stats in teams_stats.items():
            gd = stats["Goals For"] - stats["Goals Against"]
            rows.append({
                "League": league_name,
                "Team": team,
                "Matches": stats["Matches"],
                "Points": stats["Points"],
                "Goals For": stats["Goals For"],
                "Goals Against": stats["Goals Against"],
                "Goal Difference": gd
            })
            
        rows.sort(key=lambda x: (x["Points"], x["Goal Difference"], x["Goals For"]), reverse=True)
        return rows
    except Exception as e:
        print(f"解析 {league_name} 异常: {e}")
        return []

def main():
    print("Starting Football Data Scraper...")
    all_rows = []

    for league_name, url in LEAGUES_DATA.items():
        rows = fetch_data(league_name, url)
        if rows:
            all_rows.extend(rows)

    if not all_rows:
        print("⚠️ 未能从远程拉取到实时赛果，生成基础数据表确保流程通畅...")
        all_rows.append({
            "League": "Premier League",
            "Team": "System Notice",
            "Matches": 0,
            "Points": 0,
            "Goals For": 0,
            "Goals Against": 0,
            "Goal Difference": 0
        })

    df = pd.DataFrame(all_rows)
    output_file = "football_standings_stats.xlsx"
    
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Standings", index=False)

    print(f"Output Excel: {output_file}")
    caption = f"⚽ *足球联赛数据报表*\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    send_telegram_document(output_file, caption)

if __name__ == "__main__":
    main()
