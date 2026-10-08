import os, time, requests
from datetime import datetime
from openpyxl import Workbook

T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")
KEY = os.environ.get("BIGBALLS_API_KEY")
BASE = "https://api.bigballsdata.com"

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
    except Exception as e:
        print("发送失败:", e)

def api_get(path):
    r = requests.get(
        f"{BASE}{path}",
        headers={"Authorization": f"Bearer {KEY}", "Accept": "application/json"},
        timeout=20,
    )
    print(f"{path} -> {r.status_code}")
    if r.status_code != 200:
        print(r.text[:200])
        return None
    return r.json()

def extract_items(data):
    if not data:
        return []
    block = data.get("data", data)
    if isinstance(block, dict):
        inj = block.get("injuries", block)
        if isinstance(inj, dict) and "value" in inj:
            return inj["value"] if isinstance(inj["value"], list) else []
        if isinstance(inj, list):
            return inj
    if isinstance(block, list):
        return block
    return []

def team_name(team_id, cache):
    if not team_id:
        return ""
    if team_id in cache:
        return cache[team_id]
    data = api_get(f"/v1/teams/{team_id}?sport=football")
    time.sleep(0.3)
    name = team_id
    if data:
        d = data.get("data", data)
        if isinstance(d, dict):
            name = d.get("name") or d.get("full_name") or d.get("display_name") or team_id
    cache[team_id] = name
    return name

def main():
    if not KEY:
        print("缺少 BIGBALLS_API_KEY")
        return

    data = api_get("/v1/injuries?league=EPL")
    if not data:
        data = api_get("/v1/injuries?league=premier-league")
    items = extract_items(data)
    print(f"伤停名单 {len(items)} 人")

    cache = {}
    rows = []
    for it in items:
        if not isinstance(it, dict):
            continue
        player = it.get("full_name") or it.get("display_name") or ""
        tid = it.get("current_team_id") or it.get("team_id") or ""
        team = team_name(tid, cache)
        rows.append({"球队": team, "球员": player, "team_id": tid, "player_id": it.get("id")})

    rows.sort(key=lambda x: (x["球队"], x["球员"]))

    wb = Workbook()
    ws = wb.active
    ws.title = "英超伤停名单"
    ws.append(["球队", "球员"])
    for r in rows:
        ws.append([r["球队"], r["球员"]])

    # 按队汇总一页，方便看
    ws2 = wb.create_sheet("按队汇总")
    ws2.append(["球队", "伤停人数", "球员列表"])
    by_team = {}
    for r in rows:
        by_team.setdefault(r["球队"], []).append(r["球员"])
    for team in sorted(by_team.keys()):
        ps = by_team[team]
        ws2.append([team, len(ps), "、".join(ps)])

    fname = f"injuries_epl_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    wb.save(fname)
    send_file(fname, caption=f"英超伤停名单\n{len(rows)} 人 / {len(by_team)} 队")
    print("已发送:", fname)

if __name__ == "__main__":
    main()
