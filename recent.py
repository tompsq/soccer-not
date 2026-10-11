import os
import csv
from datetime import datetime, timedelta, timezone
import requests

TELEGRAM_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TG_CHAT_ID")

# football-data.co.uk 针对当前 2025/26 赛季（路径为 mmz4281/2526/）的联赛代号映射
LEAGUES_CONFIG = {
    "Premier League": "E0",
    "Championship": "E1",
    "La Liga": "SP1",
    "Serie A": "I1",
    "Bundesliga": "D1",
    "Ligue 1": "F1",
    "Primeira Liga": "P1",
    "Pro League": "B1",
    "Premiership": "SC0",
    "Super Lig": "T1",
    "Super League Greece": "G1"
}

def fetch_and_save_matches():
    utc_plus_8 = timezone(timedelta(hours=8))
    now_bj = datetime.now(utc_plus_8)
    three_days_ago = now_bj - timedelta(days=3)
    
    start_date = three_days_ago.date()
    end_date = now_bj.date()
    
    print(f"【公开CSV抓取】目标日期范围: {start_date} 至 {end_date}")
    
    rows = [["Season", "Date", "League_Name", "Source", "Home_Team", "Away_Team", "Home_Goals", "Away_Goals", "Status"]]
    total_matches = 0
    season_code = "2526"
    
    for league_name, code in LEAGUES_CONFIG.items():
        csv_url = f"https://www.football-data.co.uk/mmz4281/{season_code}/{code}.csv"
        try:
            res = requests.get(csv_url, timeout=15)
            if res.status_code == 200:
                content = res.content.decode('utf-8', errors='ignore')
                lines = content.splitlines()
                reader = csv.reader(lines)
                
                header = next(reader, None)
                if not header:
                    continue
                
                date_idx = header.index("Date") if "Date" in header else 1
                home_idx = header.index("HomeTeam") if "HomeTeam" in header else 2
                away_idx = header.index("AwayTeam") if "AwayTeam" in header else 3
                hg_idx = header.index("FTHG") if "FTHG" in header else 4
                ag_idx = header.index("FTAG") if "FTAG" in header else 5
                
                league_count = 0
                for row in reader:
                    if len(row) <= max(date_idx, home_idx, away_idx, hg_idx, ag_idx):
                        continue
                    
                    date_str = row[date_idx].strip()
                    if not date_str:
                        continue
                    
                    match_date = None
                    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
                        try:
                            match_date = datetime.strptime(date_str, fmt).date()
                            break
                        except ValueError:
                            continue
                    
                    if match_date and start_date <= match_date <= end_date:
                        home_team = row[home_idx].strip()
                        away_team = row[away_idx].strip()
                        try:
                            hg = int(row[hg_idx].strip())
                            ag = int(row[ag_idx].strip())
                        except ValueError:
                            continue
                        
                        rows.append([
                            "2025/26", 
                            match_date.strftime("%Y-%m-%d"), 
                            league_name, 
                            "Public-CSV", 
                            home_team, 
                            away_team, 
                            hg, 
                            ag, 
                            "FINISHED"
                        ])
                        total_matches += 1
                        league_count += 1
                
                print(f"[{league_name}] 抓取成功，命中目标时间段比赛: {league_count} 场")
            else:
                print(f"[{league_name}] CSV下载失败，状态码: {res.status_code}")
        except Exception as e:
            print(f"[{league_name}] 异常: {e}")

    output_file = "recent_finished_matches.csv"
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
        
    print(f"所有公开 CSV 联赛解析完毕，共计有效比赛 {total_matches} 场。")
    return output_file

def send_to_telegram(file_path):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
        
    token = TELEGRAM_BOT_TOKEN.strip()
    chat_id = TELEGRAM_CHAT_ID.strip()
    
    text_url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(text_url, data={
        "chat_id": chat_id,
        "text": "⚽ GitHub Actions: 11个目标联赛（基于公开 CSV 宝库）过去三天赛果已全部同步完毕，请查收档案："
    })
    
    doc_url = f"https://api.telegram.org/bot{token}/sendDocument"
    with open(file_path, "rb") as f:
        files = {"document": f}
        data = {"chat_id": chat_id}
        requests.post(doc_url, data=data, files=files)

if __name__ == "__main__":
    file_name = fetch_and_save_matches()
    if file_name:
        send_to_telegram(file_name)
