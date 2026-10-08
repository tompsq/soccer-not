import os, requests
from datetime import datetime
from openpyxl import Workbook

T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")
KEY = os.environ.get("BIGBALLS_API_KEY")
BASE = "https://api.bigballsdata.com"

TEAM_MAP = {
    "bb_team_6xvcggo6fhj6": "Chelsea",
    "bb_team_6zmcfvtdqosl": "Sunderland",
    "bb_team_bku3akfbg5he": "Arsenal",
    "bb_team_bmnmmt2dqbek": "Aston Villa",
    "bb_team_e724gf4htpnl": "Brentford",
    "bb_team_efzvjqit6wuk": "Leicester",
    "bb_team_eoiz65w56j7g": "Tottenham",
    "bb_team_l6apkmfeheu6": "Brighton",
    "bb_team_o7j63lsrekzf": "Bournemouth",
    "bb_team_p6t3w2ul5sel": "Manchester United",
    "bb_team_y5cv6htoh5hu": "Fulham",
    "bb_team_y72vuylsqou7": "Fulham",
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
    except Exception as e:
        print("发送失败:", e)

def extract_items(data):
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

    r = requests.get(
        f"{BASE}/v1/injuries?league=EPL",
        headers={"Authorization": f"Bearer {KEY}", "Accept": "application/json"},
        timeout=20,
    )
    print("状态码:", r.status_code)
    if r.status_code != 200:
        print(r.text[:200])
        return

    items = extract_items(r.json())
    print(f"伤停 {len(items)} 人")

    rows = []
    unknown_ids = set()
    for it in items:
        if not isinstance(it, dict):
            continue
        player = it.get("full_name") or it.get("display_name") or ""
        tid = it.get("current_team_id") or ""
        team = TEAM_MAP.get(tid)
        if not team:
            team = tid
            if tid:
                unknown_ids.add(tid)
        rows.append({"球队": team, "球员": player, "team_id": tid})

    rows.sort(key=lambda x: (x["球队"], x["球员"]))

    wb = Workbook()
    ws = wb.active
    ws.title = "英超伤停名单"
    ws.append(["球队", "球员"])
    for r in rows:
        ws.append([r["球队"], r["球员"]])

    ws2 = wb.create_sheet("按队汇总")
    ws2.append(["球队", "人数", "球员"])
    by_team = {}
    for r in rows:
        by_team.setdefault(r["球队"], []).append(r["球员"])
    for team in sorted(by_team.keys()):
        ps = by_team[team]
        ws2.append([team, len(ps), "、".join(ps)])

    if unknown_ids:
        ws3 = wb.create_sheet("未知team_id")
        ws3.append(["team_id", "说明"])
        for tid in sorted(unknown_ids):
            ws3.append([tid, "请补进 TEAM_MAP"])

    fname = f"injuries_epl_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    wb.save(fname)
    ok = sum(1 for r in rows if r["球队"] in TEAM_MAP.values())
    send_file(fname, caption=f"英超伤停名单\n{len(rows)} 人，已识别队名约 {ok} 人")
    print("未知 team_id:", unknown_ids)
    print("已发送:", fname)

if __name__ == "__main__":
    main()
