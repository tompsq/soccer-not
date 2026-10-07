import os
import time
import requests
import pandas as pd
from datetime import datetime

# 替换为 Football-Data.org 的公开 API 端点（支持各大主流联赛）
# 注：如果你申请了免费的 X-Auth-Token 密钥可以在 headers 里加上，不加也可以直接请求部分公开数据
BASE_URL = "https://api.football-data.org/v4"

# 联赛代码对应表
LEAGUES = {
    "Premier League": "PL",
    "La Liga": "PD",
    "Bundesliga": "BL1",
    "Serie A": "SA",
    "Ligue 1": "FL1",
    "Championship": "ELC"
}

# 也可以配置你在 Github Secrets 里的 API Key（如果有的话）
FOOTBALL_DATA_API_KEY = os.environ.get("FOOTBALL_DATA_API_KEY", "")

HEADERS = {
    "X-Auth-Token": FOOTBALL_DATA_API_KEY
} if FOOTBALL_DATA_API_KEY else {}

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
                print("✅ 真实赛场与积分数据报表已成功发送到 Telegram！")
            else:
                print(f"❌ 发送失败: {resp.text}")
    except Exception as e:
        print(f"TG 发送异常: {e}")

def get_json(url):
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.json()

def fetch_league_standings(league_name, competition_code):
    """从稳定接口获取官方真实积分榜及进失球数据"""
    url = f"{BASE_URL}/competitions/{competition_code}/standings"
    print(f"正在获取 {league_name} 真实积分与战绩数据...")
    
    try:
        data = get_json(url)
        standings = data.get("standings", [])
        
        # 寻找总积分榜 (TOTAL)
        total_table = None
        for s in standings:
            if s.get("type") == "TOTAL":
                total_table = s.get("table", [])
                break
                
        if not total_table:
            return []
            
        season_info = data.get("season", {})
        season_name = f"{season_info.get('startDate', '')[:4]}/{season_info.get('endDate', '')[:4]}"
        
        league_rows = []
        for row in total_table:
            team_name = row.get("team", {}).get("name", "Unknown")
            played = row.get("playedGames", 0)
            pts = row.get("points", 0)
            gf = row.get("goalsFor", 0)
            ga = row.get("goalsAgainst", 0)
            gd = row.get("goalDifference", 0)
            
            league_rows.append({
                "League": league_name,
                "Season": season_name,
                "Team": team_name,
                "Matches": played,
                "Points": pts,
                "Goals For": gf,
                "Goals Against": ga,
                "Goal Difference": gd
            })
            
        return league_rows
        
    except Exception as e:
        print(f"获取 {league_name} 数据失败: {e}")
        return []

def main():
    print("Starting Stable Football Data Scraper...")
    all_rows = []

    for league_name, code in LEAGUES.items():
        print("\n" + "=" * 50)
        print(f"Processing: {league_name}")
        print("=" * 50)
        
        rows = fetch_league_standings(league_name, code)
        if rows:
            all_rows.extend(rows)
            
        time.sleep(0.5) # 友好的请求间隔

    df = pd.DataFrame(all_rows)
    if df.empty:
        raise Exception("No data collected from API.")

    output_file = "football_standings_stats.xlsx"
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Standings & Stats", index=False)

    print("\n" + "=" * 50)
    print("DONE")
    print("=" * 50)
    print(f"Total Teams: {len(df)}")
    print(f"Output: {output_file}")

    caption = f"⚽ *官方稳定赛场数据报表*\n📊 涵盖各大主流联赛实时积分与净胜球\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    send_telegram_document(output_file, caption)

if __name__ == "__main__":
    main()
