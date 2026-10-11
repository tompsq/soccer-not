import os
import csv
from datetime import datetime, timedelta
import requests

# 从 GitHub Secrets 读取配置
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 定义你需要监控的联赛字典 { 联赛名称: 联赛ID }
LEAGUES = {
    "Premier League": 39,       # 英超
    "La Liga": 140,             # 西甲
    "Serie A": 135,             # 意甲
    "Bundesliga": 78,           # 德甲
    "Ligue 1": 61,              # 法甲
    "Championship": 40,         # 英冠
    "Primeira Liga": 94,        # 葡超
    "Pro League": 144,          # 比甲 (比利时甲级联赛)
    "Premiership": 179,         # 苏超 (苏格兰超级联赛)
    "Super Lig": 203,           # 土超 (土耳其超级联赛)
    "Super League": 197         # 希超 (希腊超级联赛)
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
        "x-rapidapi-key": API_FOOTBALL_KEY
    }
    
    # 构建长表 (Tidy Data) 结构
    rows = [["Season", "Date", "League_Name", "League_ID", "Home_Team", "Away_Team", "Home_Goals", "Away_Goals", "Status"]]
    
    total_matches = 0
    
    # 循环遍历每一个联赛
    for league_name, league_id in LEAGUES.items():
        params = {
            "league": league_id,
            "season": 2026,    # 当前赛季年份
            "from": from_date,
            "to": to_date,
            "status": "FT"     # 已结束比赛
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            if response.status_code == 200:
                fixtures = response.json().get("response", [])
                print(f"[{league_name}] 获取到 {len(fixtures)} 场已结束比赛。")
                
                for match in fixtures:
                    fixture_info = match.get("fixture", {})
                    teams_info = match.get("teams", {})
                    goals_info = match.get("goals", {})
                    
                    match_date = fixture_info.get("date", "")[:10]
                    home_team = teams_info.get("home", {}).get("name", "")
                    away_team = teams_info.get("away", {}).get("name", "")
                    home_goals = goals_info.get("home", 0)
                    away_goals = goals_info.get("goals", {}).get("home", 0) if goals_info.get("away") is not None else 0 # 防止None值
                    # 修正进球提取
                    h_goals = goals_info.get("home") if goals_info.get("home") is not None else 0
                    a_goals = goals_info.get("away") if goals_info.get("away") is not None else 0
                    
                    status = fixture_info.get("status", {}).get("short", "")
                    
                    rows.append(["2026/27", match_date, league_name, league_id, home_team, away_team, h_goals, a_goals, status])
                    total_matches += 1
            else:
                print(f"[{league_name}] 请求失败，状态码: {response.status_code}")
        except Exception as e:
            print(f"[{league_name}] 请求异常: {e}")

    print(f"所有目标联赛抓取完毕，共计 {total_matches} 场比赛。")
    
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
        "text": "⚽ GitHub Actions: 五大联赛及比甲/苏超/葡超/英冠/土超/希超过去三天赛果已打包，请查收 CSV 档案："
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
