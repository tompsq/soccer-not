import os, time, requests
from datetime import datetime
from openpyxl import Workbook

T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")
KEY = os.environ.get("BIGBALLS_API_KEY")
BASE = "https://api.bigballsdata.com"
MAX_DETAIL = 20  # 先只查明细 20 人，避免一天额度用完

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

def main():
    if not KEY:
        print("缺少 BIGBALLS_API_KEY")
        return

    # 1) 名单（文档支持 EPL）
    data = api_get("/v1/injuries?league=EPL")
    if not data:
        return

    items = []
    block = data.get("data", data)
    if isinstance(block, dict):
        inj = block.get("injuries", block)
        if isinstance(inj, dict) and "value" in inj:
            items = inj["value"]
        elif isinstance(inj, list):
            items = inj
    elif isinstance(block, list):
        items = block

    print(f"名单 {len(items)} 人")

    rows = []
    for i, it in enumerate(items[:MAX_DETAIL]):
        if not isinstance(it, dict):
            continue
        pid = it.get("id")
        name = it.get("full_name") or it.get("display_name") or ""
        if not pid:
            continue

        detail = api_get(f"/v1/players/{pid}/injury")
        time.sleep(0.35)

        status = reason = ret = comment = team = None
        if detail:
            d = detail.get("data", detail)
            status = d.get("status")
            reason = d.get("injury_type") or d.get("reason")
            ret = d.get("return_date")
            comment = d.get("comment")
            player = d.get("player") or {}
            team_obj = player.get("team") or {}
            team = team_obj.get("name") if isinstance(team_obj, dict) else None
            if not name:
                name = player.get("name") or name

        rows.append({
            "球员": name,
            "球队": team or it.get("current_team_id"),
            "状态": status,
            "伤情": reason,
            "预计回归": ret,
            "备注": comment,
            "player_id": pid,
        })
        print(f"  [{i+1}] {name} | {team} | {status} | {reason}")

    wb = Workbook()
    ws = wb.active
    ws.title = "英超伤停"
    headers = ["球员", "球队", "状态", "伤情", "预计回归", "备注", "player_id"]
    ws.append(headers)
    for r in rows:
        ws.append([r.get(h) for h in headers])

    fname = f"injuries_bigballs_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    wb.save(fname)
    send_file(fname, caption=f"BigBalls 英超伤停明细\n查了前 {len(rows)} 人（省额度）")
    print("已发送:", fname)

if __name__ == "__main__":
    main()
