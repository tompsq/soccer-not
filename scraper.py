import os
import csv
from datetime import datetime, timedelta
import requests

# 从 GitHub Secrets 读取配置
FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TG_CHAT_ID")

# Football-Data.org 的竞赛代码映射字典 { 联赛名称: 竞赛代码 }
LEAGUES = {
    "Premier League": "PL",       # 英超
    "La Liga": "PD",              # 西甲
    "Serie A": "SA",              # 意甲
    "Bundesliga": "BL1",          # 德甲
    "Ligue 1": "FL1",             # 法甲
    "Championship": "EL",         # 英冠
    "Primeira Liga": "PPL",       # 葡超
    "Pro League": "D1",           # 比甲 (比利时)
    "Premiership": "SCO",         # 苏超 (苏格兰)
    "Super Lig": "TSL",           # 土超 (土耳其)
    # 注：Football-Data 免费版可能未包含希腊超级联赛(Super League Greece)，若报错可暂注释，此处保留映射
    "Super League Greece": "GRC"  # 希超
}

def fetch_and_save_matches():
    today = datetime.now()
    three_days_ago = today - timedelta(days=3)
    
    from_date = three_days_ago.strftime("%Y-%m-%d")
    to_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    
    print(f"正在通过 Football-Data 获取 {from_date} 至 {to_date} 期间的赛事...")
    
    headers = {
        "X-Auth-Token": FOOTBALL_DATA_API_KEY.strip() if FOOTBALL_DATA_API_KEY else ""
    }
    
    rows = [["Season", "Date", "League_Name", "League_Code", "Home_Team", "Away_Team", "Home_Goals", "Away_Goals", "Status"]]
    total_matches = 0
    
    for league_name, league_code in LEAGUES.items():
        # Football-Data 的赛程按日期查询接口
        url = f"https://api.football-data.org/v4/competitions/{league_code}/matches"
        params = {
            "dateFrom": from_date,
            "dateTo": to_date,
            "status": "FINISHED" # 已结束的比赛
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                matches = data.get("matches", [])
                print(f"[{league_name}] 获取成功，共 {len(matches)} 场已结束比赛。")
                
                for match in matches:
                    match_date = match.get("utcDate", "")[:10]
                    home_team = match.get("homeTeam", {}).get("name", "")
                    away_team = match.get("awayTeam", {}).get("name", "")
                    
                    score = match.get("score", {}).get("fullTime", {})
                    h_goals = score.get("home") if score.get("home") is not None else 0
                    a_goals = score.get("away") if score.get("away") is not None else 0
                    status = match.get("status", "")
                    
                    # 确定赛季年份标识（可根据当前月份动态或默认 2025/26）
                    season_str = "2025/26"
                    
                    rows.append([season_str, match_date, league_name, league_code, home_team, away_team, h_goals, a_goals, status])
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
        "text": "⚽ GitHub Actions (Football-Data): 过去三天赛果已抓取完毕，请查收 CSV 档案："
    })
    print(f"Telegram 文本消息响应状态: {res_text.status_code}")
    
    # 2. 发送 CSV 文件
    doc_url = f"https://api.telegram.org/bot{token}/sendDocument"
    with open(file_path, "rb") as f:
        files = {"document": f}
        data = {"chat_id": chat_id}
        res_doc = requests.post(doc_url, data=data, files=files)
        
    print(f"Telegram 文件发送响应状态: {res_doc.status_code}")

if __name__ == "__main__":
    file_name = fetch_and_save_matches()
    if file_name:
        send_to_telegram(file_name)
