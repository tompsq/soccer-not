import os, time, requests
from datetime import datetime
from openpyxl import Workbook

T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")
API_KEY = os.environ.get("API_FOOTBALL_KEY")  # 你的 API-Football Key

# 联赛 ID（API-Football）
LEAGUES = [
    ("英超", 39),
    ("西甲", 140),
    ("意甲", 135),
    ("德甲", 78),
    ("英冠", 40),
    ("葡超", 94),
    ("苏超", 179),
    ("比甲", 144),
    ("土超", 203),
    ("欧冠", 2),
    ("欧联", 3),
]

H = {
    "x-apisports-key": API_KEY,
}

def send_file(path, caption=""):
    if not T or not C:
        print("文件已生成:", path)
        return
    try:
        with open(path, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{T}/sendDocument",
                data={"chat_id": C, "caption": caption},
                files={"document": f},
                timeout=60,
            )
        time.sleep(1)
    except Exception as e:
        print("发送失败:", e)

def get_injuries(league_id, season=2026):
    """获取某联赛伤停（1次请求）"""
    url = "https://v3.football.api-sports.io/injuries"
    params = {"league": league_id, "season": season}
    try:
        r = requests.get(url, headers=H, params=params, timeout=20)
        if r.status_code != 200:
            print(f"联赛 {league_id} 状态码 {r.status_code}")
            return []
        data = r.json()
        return data.get("response", [])
    except Exception as e:
        print(f"联赛 {league_id} 错误: {e}")
        return []

def main():
    if not API_KEY:
        print("缺少 API_FOOTBALL_KEY")
        return

    print("开始抓取伤停...")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    all_rows = []
    used = 0

    for name, lid in LEAGUES:
        print(f"抓取 {name}...")
        items = get_injuries(lid)
        used += 1
        print(f"  → {len(items)} 条")

        for item in items:
            player = item.get("player", {})
            team = item.get("team", {})
            fixture = item.get("fixture", {})
            league = item.get("league", {})

            all_rows.append({
                "联赛": name,
                "球队": team.get("name", ""),
                "球员": player.get("name", ""),
                "类型": player.get("type", ""),  # Missing / Injured 等
                "原因": player.get("reason", ""),
                "比赛ID": fixture.get("id", ""),
            })
        time.sleep(1.2)  # 避免过快

    print(f"本次共用请求约 {used} 次")

    if not all_rows:
        print("没有抓到伤停数据")
        return

    wb = Workbook()
    ws = wb.active
    ws.title = "伤停"
    headers = ["联赛", "球队", "球员", "类型", "原因", "比赛ID"]
    ws.append(headers)
    for r in all_rows:
        ws.append([r.get(h) for h in headers])

    fname = f"injuries_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    wb.save(fname)
    send_file(fname, caption=f"各大联赛伤停 {ts}\n共 {len(all_rows)} 条\n用了约 {used} 次请求")
    print("已发送:", fname)

if __name__ == "__main__":
    main()
