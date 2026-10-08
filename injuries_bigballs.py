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

def main():
    if not KEY:
        print("缺少 BIGBALLS_API_KEY")
        return

    headers = {
        "Authorization": f"Bearer {KEY}",
        "Accept": "application/json",
    }

    # 常见伤停相关路径（按文档可能需微调）
    urls = [
        f"{BASE}/v1/injuries?league=premier-league",
        f"{BASE}/v1/soccer/injuries?league=premier-league",
        f"{BASE}/v1/leagues/premier-league/injuries",
        f"{BASE}/v1/football/injuries?league=EPL",
    ]

    rows = []
    ok_url = None
    raw_sample = None

    for url in urls:
        print(f"尝试: {url}")
        try:
            r = requests.get(url, headers=headers, timeout=20)
            print(f"  状态码: {r.status_code}")
            print(f"  前200字: {r.text[:200]}")
            if r.status_code == 200:
                data = r.json()
                ok_url = url
                raw_sample = data
                # 尽量兼容 list / dict
                items = data if isinstance(data, list) else data.get("data") or data.get("injuries") or data.get("results") or []
                if isinstance(items, dict):
                    items = items.get("items") or list(items.values())
                if not isinstance(items, list):
                    items = [data]
                for it in items[:80]:
                    if not isinstance(it, dict):
                        continue
                    rows.append({
                        "player": it.get("player") or it.get("player_name") or it.get("name"),
                        "team": it.get("team") or it.get("team_name") or it.get("club"),
                        "status": it.get("status") or it.get("type") or it.get("reason"),
                        "reason": it.get("reason") or it.get("injury") or it.get("description"),
                        "return": it.get("return_date") or it.get("expected_return") or it.get("until"),
                        "raw_keys": ",".join(it.keys())[:80],
                    })
                break
        except Exception as e:
            print(f"  错误: {e}")

    wb = Workbook()
    ws = wb.active
    ws.title = "伤停测试"

    if rows:
        headers_row = ["player", "team", "status", "reason", "return", "raw_keys"]
        ws.append(headers_row)
        for r in rows:
            ws.append([r.get(h) for h in headers_row])
        print(f"解析到 {len(rows)} 条")
    else:
        ws.append(["result", "detail"])
        ws.append(["无结构化数据", f"ok_url={ok_url}"])
        ws.append(["sample", str(raw_sample)[:2000] if raw_sample else "无"])
        print("未解析到列表，已写入原始 sample")

    fname = f"injuries_bigballs_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    wb.save(fname)
    send_file(fname, caption=f"BigBalls 英超伤停测试\nurl={ok_url or 'none'}\n条数={len(rows)}")
    print("已发送:", fname)

if __name__ == "__main__":
    main()
