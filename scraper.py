import os
import csv
from datetime import datetime, timedelta
import requests

# 直接从 GitHub Repository Secrets (环境变量) 中读取
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def fetch_and_save_matches():
    today = datetime.now()
    three_days_ago = today - timedelta(days=3)
    
    from_date = three_days_ago.strftime("%Y-%m-%d")
    to_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    
    print(f"正在通过 API 获取 {from_date} 至 {to_date} 的已结束赛事...")
    
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {
        "x-rapidapi-host": "v3.football.api-sports.io",
        "x-rapidapi-key": API_FOOTBALL_KEY
    }
    params = {
        "league": 39,      # 英超联赛 ID
        "season": 2026,    # 当前赛季年份
        "from": from_date,
        "to": to_date,
        "status": "FT"     # 已结束比赛
    }
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"API 请求失败: {response.text}")
        return None
        
    fixtures = response.json().get("response", [])
    print(f"成功获取到 {len(fixtures)} 场比赛。")
    
    # 组装竖向长表 (Tidy Data) 结构
    rows = [["Season", "Date", "League_ID", "Home_Team", "Away_Team", "Home_Goals", "Away_Goals", "Status"]]
    
    for match in fixtures:
        fixture_info = match.get("fixture", {})
        teams_info = match.get("teams", {})
        goals_info = match.get("goals", {})
        
        match_date = fixture_info.get("date", "")[:10]
        home_team = teams_info.get("home", {}).get("name", "")
        away_team = teams_info.get("away", {}).get("name", "")
        home_goals = goals_info.get("home", 0)
        away_goals = goals_info.get("away", 0)
        status = fixture_info.get("status", {}).get("short", "")
        
        rows.append(["2026/27", match_date, 39, home_team, away_team, home_goals, away_goals, status])
        
    output_file = "recent_finished_matches.csv"
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
        
    return output_file

def send_to_telegram(file_path):
    if not os.path.exists(file_path):
        print("未找到文件，取消推送。")
        return
        
    print("正在通过 Telegram 推送结果...")
    
    # 1. 发送提示消息
    text_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(text_url, data={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": "⚽ GitHub Actions: 过去三天的赛事数据已抓取完毕，请查收 CSV 档案："
    })
    
    # 2. 发送 CSV 文件
    doc_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    with open(file_path, "rb") as f:
        files = {"document": f}
        data = {"chat_id": TELEGRAM_CHAT_ID}
        response = requests.post(doc_url, data=data, files=files)
        
    if response.status_code == 200:
        print("Telegram 推送成功！")
    else:
        print(f"Telegram 推送失败: {response.text}")

if __name__ == "__main__":
    file_name = fetch_and_save_matches()
    if file_name:
        send_to_telegram(file_name)
