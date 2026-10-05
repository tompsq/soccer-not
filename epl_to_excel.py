import os
import time
from datetime import datetime
from curl_cffi import requests  # 关键：使用 curl_cffi 代替普通的 requests
from openpyxl import Workbook

TOURNAMENT_ID = 17
SEASONS_URL = f"https://api.sofascore.com/api/v1/unique-tournament/{TOURNAMENT_ID}/seasons"

TG_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

def get_json(url):
    try:
        # impersonate="chrome110" 会完美伪造浏览器的 TLS 指纹，直接绕过 403
        response = requests.get(url, impersonate="chrome110", timeout=15)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"请求失败状态码: {response.status_code}, URL: {url}")
    except Exception as e:
        print(f"请求异常: {e}, URL: {url}")
    return None

def send_file(filepath):
    if not TG_TOKEN or not TG_CHAT_ID:
        print("未配置 TG，文件在本地:", filepath)
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendDocument"
    try:
        with open(filepath, "rb") as f:
            files = {"document": f}
            data = {"chat_id": TG_CHAT_ID}
            # TG 发送文件也用 curl_cffi 保持一致
            requests.post(url, data=data, files=files, timeout=60)
            print("✅ Excel 档案已成功发送到 Telegram！")
    except Exception as e:
        print(f"发送文件异常: {e}")

def main():
    print("开始执行英超数据抓取...")
    seasons_data = get_json(SEASONS_URL)
    if not seasons_data or "seasons" not in seasons_data:
        print("❌ 获取赛季失败:", seasons_data)
        return

    season_id = seasons_data["seasons"][0]["id"]
    print(f"✅ 成功获取 Season ID: {season_id}")

    # 1. 获取英超积分榜
    standings_url = f"https://api.sofascore.com/api/v1/unique-tournament/{TOURNAMENT_ID}/season/{season_id}/standings/total"
    standings_data = get_json(standings_url)

    teams_data = []
    if standings_data and "standings" in standings_data:
        rows = standings_data["standings"][0].get("rows", [])
        for row in rows:
            team = row["team"]
            teams_data.append({
                "team_id": team["id"],
                "team_name": team["name"],
                "position": row.get("position"),
                "points": row.get("points"),
                "played": row.get("matchesPlayed"),
            })
    print(f"✅ 成功解析球队数量: {len(teams_data)}")

    # 2. 循环获取每支球队 xG 与伤停
    team_stats_list = []
    injury_list = []

    for t in teams_data:
        t_id = t["team_id"]
        t_name = t["team_name"]

        # 赛季统计 (xG)
        stats_url = f"https://api.sofascore.com/api/v1/team/{t_id}/tournament/{TOURNAMENT_ID}/season/{season_id}/statistics/overall"
        stats_res = get_json(stats_url)

        xg_for = 0.0
        xg_against = 0.0
        if stats_res and "statistics" in stats_res:
            xg_for = stats_res["statistics"].get("expectedGoals", 0.0)
            xg_against = stats_res["statistics"].get("expectedGoalsConceded", 0.0)

        team_stats_list.append({
            "排名": t["position"],
            "球队": t_name,
            "场次": t["played"],
            "积分": t["points"],
            "预期进球(xG)": xg_for,
            "预期失球(xGA)": xg_against
        })

        # 伤停数据
        inj_url = f"https://api.sofascore.com/api/v1/team/{t_id}/injuries"
        inj_res = get_json(inj_url)
        if inj_res and "injuries" in inj_res:
            for inj in inj_res["injuries"]:
                player = inj.get("player", {})
                injury_list.append({
                    "球队": t_name,
                    "球员": player.get("name"),
                    "位置": player.get("position"),
                    "伤停类型": inj.get("incidentClass"),
                    "预计回归时间": inj.get("startDate")
                })
        time.sleep(0.3)

    # 3. 生成双 Sheet Excel
    wb = Workbook()
    
    ws1 = wb.active
    ws1.title = "英超xG与积分"
    if team_stats_list:
        headers1 = list(team_stats_list[0].keys())
        ws1.append(headers1)
        for row in team_stats_list:
            ws1.append([row.get(h) for h in headers1])

    ws2 = wb.create_sheet(title="伤停情报")
    if injury_list:
        headers2 = list(injury_list[0].keys())
        ws2.append(headers2)
        for row in injury_list:
            ws2.append([row.get(h) for h in headers2])
    else:
        ws2.append(["提示", "当前暂无伤停数据或未抓取到"])

    filename = f"EPL_xG_Injuries_{datetime.now().strftime('%Y%m%d')}.xlsx"
    wb.save(filename)
    print(f"✅ Excel 已成功生成: {filename}")

    send_file(filename)

if __name__ == "__main__":
    main()
