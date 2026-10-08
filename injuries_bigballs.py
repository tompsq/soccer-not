import os, requests
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

def extract_list(data):
    """兼容 data.injuries.value / data.injuries / data 等结构"""
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    # 优先路径
    inj = data.get("data", data)
    if isinstance(inj, dict):
        inj = inj.get("injuries", inj)
    if isinstance(inj, dict) and "value" in inj:
        inj = inj["value"]
    if isinstance(inj, list):
        return inj
    if isinstance(inj, dict):
        return list(inj.values())
    return []

def main():
    if not KEY:
        print("缺少 BIGBALLS_API_KEY")
        return

    headers = {
        "Authorization": f"Bearer {KEY}",
        "Accept": "application/json",
    }
    url = f"{BASE}/v1/injuries?league=premier-league"
    print("请求:", url)

    r = requests.get(url, headers=headers, timeout=20)
    print("状态码:", r.status_code)
    print("前300字:", r.text[:300])

    if r.status_code != 200:
        print("请求失败")
        return

    data = r.json()
    items = extract_list(data)
    print(f"解析到 {len(items)} 条原始记录")

    rows = []
    all_keys = set()
    for it in items:
        if not isinstance(it, dict):
            continue
        all_keys.update(it.keys())
        rows.append({
            "id": it.get("id"),
            "full_name": it.get("full_name") or it.get("display_name") or it.get("name"),
            "display_name": it.get("display_name"),
            "sport": it.get("sport"),
            "team_id": it.get("current_team_id") or it.get("team_id"),
            "status": it.get("status") or it.get("injury_status"),
            "reason": it.get("reason") or it.get("injury") or it.get("description"),
            "return": it.get("return_date") or it.get("expected_return") or it.get("until"),
            "updated": it.get("updated_at") or it.get("as_of"),
        })

    print("字段示例:", sorted(all_keys)[:30])

    wb = Workbook()
    ws = wb.active
    ws.title = "英超伤停"
    headers_row = ["id", "full_name", "display_name", "sport", "team_id", "status", "reason", "return", "updated"]
    ws.append(headers_row)
    for row in rows:
        ws.append([row.get(h) for h in headers_row])

    # 第二页：原始第一条方便核对
    if items:
        ws2 = wb.create_sheet("样例原始")
        sample = items[0]
        ws2.append(["key", "value"])
        for k, v in sample.items():
            ws2.append([k, str(v)[:500]])

    fname = f"injuries_bigballs_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    wb.save(fname)
    send_file(fname, caption=f"BigBalls 英超伤停\n共 {len(rows)} 条")
    print("已发送:", fname)

if __name__ == "__main__":
    main()
