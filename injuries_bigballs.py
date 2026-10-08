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

def main():
    if not KEY:
        print("缺少 BIGBALLS_API_KEY")
        return

    data = api_get("/v1/injuries?league=EPL")
    if not data:
        data = api_get("/v1/injuries?league=premier-league")
    if not data:
        print("名单请求失败")
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

    wb = Workbook()

    ws1 = wb.active
    ws1.title = "名单样例"
    if items:
        sample = items[0]
        ws1.append(["key", "value"])
        for k, v in sample.items():
            ws1.append([k, str(v)[:800]])
        print("名单样例 keys:", list(sample.keys()))

    ws2 = wb.create_sheet("详情样例")
    ws2.append(["player_id", "name", "http", "raw_json"])
    for it in items[:3]:
        if not isinstance(it, dict):
            continue
        pid = it.get("id")
        name = it.get("full_name") or it.get("display_name") or ""
        path = f"/v1/players/{pid}/injury"
        r = requests.get(
            f"{BASE}{path}",
            headers={"Authorization": f"Bearer {KEY}", "Accept": "application/json"},
            timeout=20,
        )
        print(f"详情 {name}: {r.status_code} {r.text[:150]}")
        ws2.append([pid, name, r.status_code, r.text[:2000]])
        time.sleep(0.4)

    ws3 = wb.create_sheet("详情展开")
    ws3.append(["key", "value"])
    if items:
        pid = items[0].get("id")
        detail = api_get(f"/v1/players/{pid}/injury")
        if detail:
            d = detail.get("data", detail)
            if isinstance(d, dict):
                for k, v in d.items():
                    ws3.append([k, str(v)[:800]])
                if isinstance(d.get("player"), dict):
                    for k, v in d["player"].items():
                        ws3.append([f"player.{k}", str(v)[:800]])

    fname = f"injuries_debug_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    wb.save(fname)
    send_file(fname, caption="BigBalls 伤停调试（看原始字段）")
    print("已发送:", fname)

if __name__ == "__main__":
    main()
