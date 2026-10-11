import os
import csv
from datetime import datetime, timedelta
import requests

# 直接对齐你 GitHub 里现有的 Secret 名字
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")     # 对应你截图中的 TG_BOT_TOKEN
TELEGRAM_CHAT_ID = os.getenv("TG_CHAT_ID")         # 对应你截图中的 TG_CHAT_ID

# 定义你需要监控的联赛字典 { 联赛名称: 联赛ID }
LEAGUES = {
    "Premier League": 39,       # 英超
    "La Liga": 140,             # 西甲
    "Serie A": 135,             # 意甲
    "Bundesliga": 78,           # 德甲
    "Ligue 1": 61,              # 法甲
    "Championship": 40,         # 英冠
    "Primeira Liga": 94,        # 葡超
    "Pro League": 144,          # 比甲
    "Premiership": 179,         # 苏超
    "Super Lig": 203,           # 土超
    "Super League": 197         # 希超
}

def fetch_and_save_matches():
    today = datetime.now()
    three_days_ago = today - timedelta(days=3)
    
    from_date = three_days_ago.strftime("%Y-%m-%d")
    to_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    
    print(f"正在获取 {from_date} 至 {to_date} 期间的指定联赛赛事...")
    
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {
        "x-rapidapi-host": "v3.football.api-sports.io",
        "x-rapidapi-key": API_FOOTBALL_KEY.strip() if API_FOOTBALL_KEY else ""
    }
    
    rows = [["Season", "Date", "League_Name", "League_ID", "Home_Team", "Away_Team", "Home_Goals", "Away_Goals", "Status"]]
    total_matches = 0
    
    for league_name, league_id in LEAGUES.items():
        params = {
            "league": league_id,
            "season": 2026,
            "from": from_date,
            "to": to_date,
            "status": "FT"
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                fixtures = data.get("response", [])
                print(f"[{league_name}] 获取成功，共 {len(fixtures)} 场已结束比赛。")
                
                for match in fixtures:
                    fixture_info = match.get("fixture", {})
                    teams_info = match.get("teams", {})
                    goals_info = match.get("goals", {})
                    
                    match_date = fixture_info.get("date", "")[:10]
                    home_team = teams_info.get("home", {}).get("name", "")
                    away_team = teams_info.get("away", {}).get("name", "")
                    
                    h_goals = goals_info.get("home") if goals_info.get("home") is not None else 0
                    a_goals = goals_info.get("away") if goals_info.get("away") is not None else 0
                    status = fixture_info.get("status", {}).get("short", "")
                    
                    rows.append(["2026/27", match_date, league_name, league_id, home_team, away_team, h_goals, a_goals, status])
                    total_matches += 1
            else:
                print(f"[{league_name}] 请求失败，状态码: {response.status_code}, 响应内容: {response.text}")
        except Exception as e:
            print(f"[{league_name}] 请求异常: {e}")

    print(f"所有目标联赛抓取完毕，共计有效比赛 {total_matches} 场。")
    
    output_file = "recent_finished_matches.csv"
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
        
    return output_file

def send_to_telegram(file_path):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("未检测到 Telegram 配置，跳过推送。")
        return
        
    if not os.path.exists(file_path):
        print("未找到需要发送的文件。")
        return
        
    print("正在通过 Telegram 推送结果...")
    
    token = TELEGRAM_BOT_TOKEN.strip()
    chat_id = TELEGRAM_CHAT_ID.strip()
    
    # 1. 发送文字提示
    text_url = f"https://api.telegram.org/bot{token}/sendMessage"
    res_text = requests.post(text_url, data={
        "chat_id": chat_id,
        "text": "⚽ GitHub Actions: 多联赛过去三天赛果已抓取完毕，请查收 CSV 档案："
    })
    print(f"Telegram 文本消息响应状态: {res_text.status_code}, 内容: {res_text.text}")
    
    # 2. 发送 CSV 文件
    doc_url = f"https://api.telegram.org/bot{token}/sendDocument"
    with open(file_path, "rb") as f:
        files = {"document": f}
        data = {"chat_id": chat_id}
        res_doc = requests.post(doc_url, data=data, files=files)
        
    print(f"Telegram 文件发送响应状态: {res_doc.status_code}, 内容: {res_doc.text}")

if __name__ == "__main__":
    file_name = fetch_and_save_matches()
    if file_name:
        send_to_telegram(file_name)
