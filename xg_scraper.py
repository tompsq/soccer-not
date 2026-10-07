import os
import requests
import pandas as pd
from datetime import datetime

# 使用 openfootball 官方维护的公开 JSON 数据库（无需任何 Key，永不 403）
LEAGUES_DATA = {
    "Premier League": "https://raw.githubusercontent.com/openfootball/eng-england/master/2025-26/1-premierleague.json",
    "La Liga": "https://raw.githubusercontent.com/openfootball/esp-spain/master/2025-26/1-primera.json",
    "Serie A": "https://raw.githubusercontent.com/openfootball/ita-italy/master/2025-26/1-seriea.json",
    "Bundesliga": "https://raw.githubusercontent.com/openfootball/deu-germany/master/2025-26/1-bundesliga.json",
    "Ligue 1": "https://raw.githubusercontent.com/openfootball/fra-france/master/2025-26/1-ligue1.json"
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

def parse_standings_from_json(league_name, url):
    print(f"正在获取 {league_name} 公开赛果数据...")
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        # 统计各支球队的积分与进失球
        teams_stats = {}
        
        rounds = data.get("rounds", [])
        for r in rounds:
            matches = r.get("matches", [])
            for m in matches:
                score = m.get("score", {})
                if not score.get("ft"):
                    continue # 未进行完的比赛跳过
                
                team1 = m.get("team1")
                team2 = m.get("team2")
                goals1 = score["ft"][0]
                goals2 = score["ft"][1]
                
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
            
        # 按积分和净胜球排序
        rows.sort(key=lambda x: (x["Points"], x["Goal Difference"], x["Goals For"]), reverse=True)
        return rows
        
    except Exception as e:
        print(f"获取 {league_name} 数据异常: {e}")
        return []

def main():
    print("Starting OpenFootball Data Scraper...")
    all_rows = []

    for league_name, url in LEAGUES_DATA.items():
        print("\n" + "=" * 50)
        rows = parse_standings_from_json(league_name, url)
        if rows:
            all_rows.extend(rows)

    if not all_rows:
        raise Exception("No data collected from openfootball source.")

    df = pd.DataFrame(all_rows)
    output_file = "football_standings_stats.xlsx"
    
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Standings", index=False)

    print("\n" + "=" * 50)
    print(f"Total Teams Processed: {len(df)}")
    print(f"Output Excel: {output_file}")

    caption = f"⚽ *公开足球联赛实时积分榜*\n📊 涵盖英超、西甲、意甲、德甲、法甲\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    send_telegram_document(output_file, caption)

if __name__ == "__main__":
    main()
