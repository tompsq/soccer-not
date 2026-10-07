import os
import requests
import pandas as pd
from datetime import datetime

# 使用公开且稳定的完整积分榜 API（直接获取整个赛季已赛完的完整积分与进失球）
LEAGUES_STANDINGS = {
    "Premier League": "https://www.thesportsdb.com/api/v1/json/3/lookuptable.php?l=4328&s=2025-2026",
    "La Liga": "https://www.thesportsdb.com/api/v1/json/3/lookuptable.php?l=4335&s=2025-2026",
    "Serie A": "https://www.thesportsdb.com/api/v1/json/3/lookuptable.php?l=4332&s=2025-2026",
    "Bundesliga": "https://www.thesportsdb.com/api/v1/json/3/lookuptable.php?l=4331&s=2025-2026",
    "Ligue 1": "https://www.thesportsdb.com/api/v1/json/3/lookuptable.php?l=4334&s=2025-2026"
}

TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")

def send_telegram_document(filepath, caption):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        print("⚠️ 未检测到 Telegram 环境变量，跳过发送。")
        return
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendDocument"
    try:
        with open(filepath, 'rb') as f:
            files = {'document': f}
            data = {'chat_id': TG_CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}
            resp = requests.post(url, data=data, files=files)
            if resp.status_code == 200:
                print("✅ 完整联赛积分榜报表已成功发送到 Telegram！")
            else:
                print(f"❌ 发送失败: {resp.text}")
    except Exception as e:
        print(f"TG 发送异常: {e}")

def fetch_standings(league_name, url):
    print(f"正在获取 {league_name} 完整积分榜...")
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            return []
        
        data = resp.json()
        table = data.get("table", [])
        if not table:
            return []
            
        rows = []
        for item in table:
            team_name = item.get("strTeam", "Unknown")
            played = int(item.get("intPlayed", 0))
            won = int(item.get("intWin", 0))
            drawn = int(item.get("intLoss", 0) and 0) # 兼容字段
            lost = int(item.get("intLoss", 0))
            gf = int(item.get("intGoalsFor", 0))
            ga = int(item.get("intGoalsAgainst", 0))
            gd = int(item.get("intGoalDifference", 0))
            points = int(item.get("intPoints", 0))
            
            rows.append({
                "League": league_name,
                "Team": team_name,
                "Matches": played,
                "Points": points,
                "Goals For": gf,
                "Goals Against": ga,
                "Goal Difference": gd
            })
            
        return rows
    except Exception as e:
        print(f"解析 {league_name} 积分榜异常: {e}")
        return []

def main():
    print("Starting Full Standings Scraper...")
    all_rows = []

    for league_name, url in LEAGUES_STANDINGS.items():
        rows = fetch_standings(league_name, url)
        if rows:
            all_rows.extend(rows)

    if not all_rows:
        raise Exception("未能成功拉取任何联赛积分榜数据。")

    df = pd.DataFrame(all_rows)
    output_file = "football_standings_stats.xlsx"
    
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Standings", index=False)

    print(f"Output Excel: {output_file}")
    caption = f"⚽ *五大联赛完整积分榜报表*\n📊 包含各队完整场次、积分与净胜球\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    send_telegram_document(output_file, caption)

if __name__ == "__main__":
    main()
