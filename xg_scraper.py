import os
import time
import requests
from datetime import datetime

BASE_URL = "https://www.sofascore.com/api/v1"

LEAGUES = {
    "Premier League": 17,
    "La Liga": 8,
    "Bundesliga": 35,
    "Serie A": 23,
    "Ligue 1": 34,
    "Championship": 18,
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Origin": "https://www.sofascore.com",
    "Referer": "https://www.sofascore.com/",
    "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
}

def get_json(url):
    # 使用 Session 保持连接，带上完整的浏览器伪装头
    session = requests.Session()
    response = session.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.json()

def get_current_season(tournament_id):
    url = f"{BASE_URL}/unique-tournament/{tournament_id}/seasons"
    data = get_json(url)
    seasons = data.get("seasons", [])
    if not seasons:
        raise Exception(f"No season found for tournament {tournament_id}")
    return seasons[0]

def get_all_events(tournament_id, season_id):
    events = []
    page = 0
    while True:
        url = f"{BASE_URL}/unique-tournament/{tournament_id}/season/{season_id}/events/last/{page}"
        try:
            data = get_json(url)
        except requests.HTTPError:
            break
        page_events = data.get("events", [])
        if not page_events:
            break
        events.extend(page_events)
        if not data.get("hasNextPage", False):
            break
        page += 1
        time.sleep(0.3)
    return events

def get_match_xg(event_id):
    url = f"{BASE_URL}/event/{event_id}/statistics"
    try:
        data = get_json(url)
    except Exception:
        return None, None

    statistics = data.get("statistics", [])
    if not statistics:
        return None, None

    full_match = None
    for period in statistics:
        if period.get("period") == "ALL":
            full_match = period
            break

    if full_match is None:
        return None, None

    home_xg = None
    away_xg = None

    for group in full_match.get("groups", []):
        for item in group.get("statisticsItems", []):
            if item.get("key") == "expectedGoals":
                home_xg = item.get("homeValue")
                away_xg = item.get("awayValue")
                if home_xg is None:
                    home_xg = item.get("home")
                if away_xg is None:
                    away_xg = item.get("away")
                break

    return home_xg, away_xg
import pandas as pd

def fetch_and_process_xg_data():
    rows = []
    print("Starting SofaScore xG scraper...")

    for league_name, tournament_id in LEAGUES.items():
        print("\n" + "=" * 50)
        print(league_name)
        print("=" * 50)

        try:
            season = get_current_season(tournament_id)
        except Exception as e:
            print(f"获取赛季失败: {e}")
            continue

        season_id = season["id"]
        season_name = season["name"]
        print(f"Season: {season_name} (ID: {season_id})")

        events = get_all_events(tournament_id, season_id)
        print(f"Events found: {len(events)}")

        teams = {}

        for event in events:
            status = event.get("status", {})
            if status.get("type") != "finished":
                continue

            home_team = event.get("homeTeam", {})
            away_team = event.get("awayTeam", {})
            home_id = home_team.get("id")
            away_id = away_team.get("id")

            if not home_id or not away_id:
                continue

            if home_id not in teams:
                teams[home_id] = {
                    "League": league_name,
                    "Team": home_team.get("name"),
                    "Matches": 0,
                    "xG": 0.0,
                    "xGA": 0.0
                }

            if away_id not in teams:
                teams[away_id] = {
                    "League": league_name,
                    "Team": away_team.get("name"),
                    "Matches": 0,
                    "xG": 0.0,
                    "xGA": 0.0
                }

            home_xg, away_xg = get_match_xg(event["id"])

            if home_xg is None or away_xg is None:
                continue

            try:
                home_xg = float(home_xg)
                away_xg = float(away_xg)
            except (ValueError, TypeError):
                continue

            teams[home_id]["Matches"] += 1
            teams[home_id]["xG"] += home_xg
            teams[home_id]["xGA"] += away_xg

            teams[away_id]["Matches"] += 1
            teams[away_id]["xG"] += away_xg
            teams[away_id]["xGA"] += home_xg

            time.sleep(0.15)

        for team in teams.values():
            matches = team["Matches"]
            team["xG"] = round(team["xG"], 2)
            team["xGA"] = round(team["xGA"], 2)

            if matches > 0:
                team["xG per Match"] = round(team["xG"] / matches, 2)
                team["xGA per Match"] = round(team["xGA"] / matches, 2)
            else:
                team["xG per Match"] = None
                team["xGA per Match"] = None

            team["Season"] = season_name
            rows.append(team)

    df = pd.DataFrame(rows)
    if df.empty:
        raise Exception("No xG data collected.")

    df = df[[
        "League", "Season", "Team", "Matches",
        "xG", "xGA", "xG per Match", "xGA per Match"
    ]]
    df = df.sort_values(["League", "xG"], ascending=[True, False])

    output_file = "sofascore_xg.xlsx"
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Season xG", index=False)

    print("\n" + "=" * 50)
    print("DONE")
    print("=" * 50)
    print(f"Teams: {len(df)}")
    print(f"Output: {output_file}")
    
    return output_file, len(df)
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
                print("✅ xG 数据报表已成功发送到 Telegram！")
            else:
                print(f"❌ 发送失败: {resp.text}")
    except Exception as e:
        print(f"TG 发送异常: {e}")

def main():
    try:
        output_file, total_teams = fetch_and_process_xg_data()
        caption = f"⚽ *SofaScore 官方 API xG 统计报表*\n📊 统计球队数: {total_teams}\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        send_telegram_document(output_file, caption)
    except Exception as e:
        print(f"程序运行出错: {e}")

if __name__ == "__main__":
    main()
