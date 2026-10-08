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
        print(r.text[:180])
        return None
    return r.json()

def as_list(data):
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    d = data.get("data", data)
    if isinstance(d, list):
        return d
    if isinstance(d, dict):
        for k in ("teams", "value", "results", "items", "standings"):
            v = d.get(k)
            if isinstance(v, list):
                return v
            if isinstance(v, dict) and isinstance(v.get("value"), list):
                return v["value"]
    return []

def build_team_map():
    """尽量从多个入口拿 team_id -> 队名"""
    paths = [
        "/v1/teams?sport=football&league=EPL",
        "/v1/teams?sport=football&league=premier-league",
        "/v1/standings?sport=football&league=EPL",
        "/v1/standings?league=EPL",
        "/v1/leagues/EPL/teams",
        "/v1/leagues/premier-league/teams",
    ]
    mapping = {}
    for path in paths:
        data = api_get(path)
        time.sleep(0.3)
        items = as_list(data)
        print(f"  {path} -> {len(items)} items")
        for it in items:
            if not isinstance(it, dict):
                continue
            # 兼容 standings 嵌套 team
            team = it.get("team") if isinstance(it.get("team"), dict) else it
            tid = team.get("id") or it.get("team_id") or it.get("id")
            name = (
                team.get("name")
                or team.get("full_name")
                or team.get("display_name")
                or it.get("team_name")
                or it.get("name")
            )
            if tid and name:
                mapping[tid] = name
        if len(mapping) >= 15:
            break
    print(f"队名映射共 {len(mapping)} 个")
    return mapping

def extract_injuries(data):
    if not data:
        return []
    block = data.get("data", data)
    if isinstance(block, dict):
        inj = block.get("injuries", block)
        if isinstance(inj, dict) and isinstance(inj.get("value"), list):
            return inj["value"]
        if isinstance(inj, list):
            return inj
    if isinstance(block, list):
        return block
    return []

def main():
    if not KEY:
        print("缺少 BIGBALLS_API_KEY")
        return

    team_map = build_team_map()

    data = api_get("/v1/injuries?league=EPL")
    if not data:
        data = api_get("/v1/injuries?league=premier-league")
    items = extract_injuries(data)
    print(f"伤停 {len(items)} 人")

    rows = []
    for it in items:
        if not isinstance(it, dict):
            continue
        player = it.get("full_name") or it.get("display_name") or ""
        tid = it.get("current_team_id") or it.get("team_id") or ""
        team = team_map.get(tid, tid)
        rows.append({"球队": team, "球员": player, "team_id": tid})

    rows.sort(key=lambda x: (x["球队"], x["球员"]))

    wb = Workbook()
    ws = wb.active
    ws.title = "英超伤停名单"
    ws.append(["球队", "球员", "team_id"])
    for r in rows:
        ws.append([r["球队"], r["球员"], r["team_id"]])

    ws2 = wb.create_sheet("按队汇总")
    ws2.append(["球队", "人数", "球员"])
    by_team = {}
    for r in rows:
        by_team.setdefault(r["球队"], []).append(r["球员"])
    for team in sorted(by_team.keys()):
        ps = by_team[team]
        ws2.append([team, len(ps), "、".join(ps)])

    # 调试：映射表
    ws3 = wb.create_sheet("队名映射")
    ws3.append(["team_id", "name"])
    for tid, name in sorted(team_map.items(), key=lambda x: x[1]):
        ws3.append([tid, name])

    fname = f"injuries_epl_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    wb.save(fname)
    resolved = sum(1 for r in rows if not str(r["球队"]).startswith("bb_team_"))
    send_file(
        fname,
        caption=f"英超伤停名单\n{len(rows)} 人，队名解析成功 {resolved} 人，映射 {len(team_map)} 队",
    )
    print("已发送:", fname)

if __name__ == "__main__":
    main()
