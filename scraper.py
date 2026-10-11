import os
import csv
from datetime import datetime, timedelta, timezone
import requests

FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TG_CHAT_ID")

FD_LEAGUES = {
    "Premier League": "PL", "La Liga": "PD", "Serie A": "SA",
    "Bundesliga": "BL1", "Ligue 1": "FL1", "Primeira Liga": "PPL"
}

ODDS_LEAGUES = {
    "Championship": "soccer_efl_champ", "Pro League": "soccer_belgium_first_div",
    "Premiership": "soccer_spl", "Super Lig": "soccer_turkey_super_league",
    "Super League Greece": "soccer_greece_super_league"
}

def fetch_and_save_matches():
    utc_plus_8 = timezone(timedelta(hours=8))
    now_bj = datetime.now(utc_plus_8)
    three_days_ago = now_bj - timedelta(days=3)
    
    from_date_str = three_days_ago.strftime("%Y-%m-%d")
    to_date_str = now_bj.strftime("%Y-%m-%d")
    
    rows = [["Season", "Date", "League_Name", "Source", "Home_Team", "Away_Team", "Home_Goals", "Away_Goals", "Status"]]
    total_matches = 0
    
    if FOOTBALL_DATA_API_KEY:
        fd_headers = {"X-Auth-Token": FOOTBALL_DATA_API_KEY.strip()}
        for name, code in FD_LEAGUES.items():
            url = f"https://api.football-data.org/v4/competitions/{code}/matches"
            try:
                res = requests.get(url, headers=fd_headers, params={"dateFrom": from_date_str, "dateTo": to_date_str, "status": "FINISHED"}, timeout=15)
                if res.status_code == 200:
                    for m in res.json().get("matches", []):
                        score = m.get("score", {}).get("fullTime", {})
                        rows.append(["2025/26", m.get("utcDate", "")[:10], name, "FD", m.get("homeTeam", {}).get("name"), m.get("awayTeam", {}).get("name"), score.get("home", 0) or 0, score.get("away", 0) or 0, m.get("status")])
                        total_matches += 1
            except: pass

    if ODDS_API_KEY:
        for name, key in ODDS_LEAGUES.items():
            url = f"https://api.the-odds-api.com/v4/sports/{key}/scores/"
            try:
                res = requests.get(url, params={"apiKey": ODDS_API_KEY.strip(), "daysFrom": 3, "dateFormat": "iso"}, timeout=15)
                if res.status_code == 200:
                    for m in [x for x in res.json() if x.get("completed")]:
                        home, away = m.get("home_team"), m.get("away_team")
                        hg, ag = 0, 0
                        for s in m.get("scores", []):
                            if s.get("name") == home: hg = int(s.get("score", 0))
                            elif s.get("name") == away: ag = int(s.get("score", 0))
                        rows.append(["2025/26", m.get("commence_time", "")[:10], name, "Odds", home, away, hg, ag, "FINISHED"])
                        total_matches += 1
            except: pass

    output_file = "recent_finished_matches.csv"
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    return output_file

def send_to_telegram(file_path):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    token, chat_id = TELEGRAM_BOT_TOKEN.strip(), TELEGRAM_CHAT_ID.strip()
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id": chat_id, "text": "⚽ 11个联赛周末赛果已多源聚合完毕，请查收 CSV档案："})
    with open(file_path, "rb") as f:
        requests.post(f"https://api.telegram.org/bot{token}/sendDocument", data={"chat_id": chat_id}, files={"document": f})

if __name__ == "__main__":
    file_name = fetch_and_save_matches()
    if file_name: send_to_telegram(file_name)
