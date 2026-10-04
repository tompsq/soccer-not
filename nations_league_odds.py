import os, time, requests, json
from datetime import datetime, timedelta
from openpyxl import Workbook

T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")

LEAGUES = [
    ("欧国联A", 200719),
    ("欧国联B", 200721),
    ("欧国联C", 200726),
    ("欧国联D", 200727),
]

H = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Origin": "https://www.pinnacle.com",
    "Referer": "https://www.pinnacle.com/",
}

def send(t):
    if not T or not C:
        print(t)
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{T}/sendMessage",
            json={"chat_id": C, "text": t[:4000], "parse_mode": "Markdown"},
            timeout=30,
        )
        time.sleep(1.2)
    except Exception as e:
        print(e)

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
        time.sleep(1.5)
    except Exception as e:
        print("发送文件失败:", e)

def to_dec(a):
    try:
        a = float(a)
        return round(a / 100 + 1, 3) if a > 0 else round(100 / abs(a) + 1, 3)
    except:
        return None

def get(url):
    for _ in range(3):
        try:
            r = requests.get(url, headers=H, timeout=20)
            if r.status_code == 200:
                return r.json()
        except:
            time.sleep(1.5)
    return None
def fetch_all():
    now_my = datetime.utcnow() + timedelta(hours=8)
    # 抓取未来 48 小时内的比赛，方便测试
    t_start = now_my
    t_end = now_my + timedelta(hours=48)

    all_matches = {}
    for name, lid in LEAGUES:
        ms = get(f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{lid}/matchups")
        if not ms:
            continue
        matches = {}
        for m in ms:
            if m.get("type") != "matchup":
                continue
            st = m.get("startTime", "")
            if not st:
                continue
            try:
                mt = datetime.strptime(st[:19], "%Y-%m-%dT%H:%M:%S") + timedelta(hours=8)
            except:
                continue
            if not (t_start <= mt <= t_end):
                continue
            ps = m.get("participants", [])
            if len(ps) < 2:
                continue
            home = next((p["name"] for p in ps if p.get("alignment") == "home"), None)
            away = next((p["name"] for p in ps if p.get("alignment") == "away"), None)
            if not home or not away or "(" in home or "(" in away:
                continue
            matches[m["id"]] = {
                "id": str(m["id"]),
                "league": name,
                "home": home,
                "away": away,
                "time": mt.strftime("%m-%d %H:%M"),
                "1X2": {},
                "ah": None,
                "ou": None,
            }
        if not matches:
            continue

       mks = get(f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{lid}/markets/straight")
        if not mks:
            continue
        for mk in mks:
            mid = mk.get("matchupId")
            if mid not in matches or mk.get("period") != 0 or mk.get("isAlternate") is True:
                continue
            t = mk.get("type")
            ps = mk.get("prices", [])
            if t == "moneyline":
                for p in ps:
                    d = p.get("designation")
                    if d in ("home", "draw", "away"):
                        matches[mid]["1X2"][d] = to_dec(p["price"])
            elif t == "spread":
                hp = next((p for p in ps if p.get("designation") == "home"), None)
                ap = next((p for p in ps if p.get("designation") == "away"), None)
                if hp and ap:
                    line = hp.get("points", 0)
                    if matches[mid]["ah"] is None or abs(line) < abs(matches[mid]["ah"][0]):
                        matches[mid]["ah"] = (line, to_dec(hp["price"]), to_dec(ap["price"]))
            elif t == "total":
                op = next((p for p in ps if p.get("designation") == "over"), None)
                up = next((p for p in ps if p.get("designation") == "under"), None)
                if op and up:
                    line = op.get("points", 0)
                    if matches[mid]["ou"] is None or abs(line - 2.5) < abs(matches[mid]["ou"][0] - 2.5):
                        matches[mid]["ou"] = (line, to_dec(op["price"]), to_dec(up["price"]))
        all_matches.update(matches)
        time.sleep(0.5)
    return all_matches

def main():
    ts = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    print(f"开始快速测试 {ts}")

    # 第 1 次抓取（开盘）
    print("第 1 次抓取...")
    snap1 = fetch_all()
    print(f"抓到 {len(snap1)} 场")
    time.sleep(120)  # 等 2 分钟

    # 第 2 次抓取
    print("第 2 次抓取...")
    snap2 = fetch_all()
    print(f"抓到 {len(snap2)} 场")
    time.sleep(120)  # 再等 2 分钟

    # 第 3 次抓取（临盘）
    print("第 3 次抓取...")
    snap3 = fetch_all()
    print(f"抓到 {len(snap3)} 场")

    # 合并数据（以第 1 次出现的比赛为基准）
    rows = []
    for mid, m1 in snap1.items():
        m3 = snap3.get(mid, m1)  # 如果第 3 次没有，就用第 1 次的
        row = {
            "联赛": m1["league"],
            "时间": m1["time"],
            "主队": m1["home"],
            "客队": m1["away"],
            "开盘主胜": m1["1X2"].get("home"),
            "开盘平局": m1["1X2"].get("draw"),
            "开盘客胜": m1["1X2"].get("away"),
            "临盘主胜": m3["1X2"].get("home"),
            "临盘平局": m3["1X2"].get("draw"),
            "临盘客胜": m3["1X2"].get("away"),
            "开盘亚盘": m1["ah"][0] if m1["ah"] else None,
            "开盘亚盘主": m1["ah"][1] if m1["ah"] else None,
            "开盘亚盘客": m1["ah"][2] if m1["ah"] else None,
            "临盘亚盘": m3["ah"][0] if m3["ah"] else None,
            "临盘亚盘主": m3["ah"][1] if m3["ah"] else None,
            "临盘亚盘客": m3["ah"][2] if m3["ah"] else None,
            "开盘大小": m1["ou"][0] if m1["ou"] else None,
            "开盘大": m1["ou"][1] if m1["ou"] else None,
            "开盘小": m1["ou"][2] if m1["ou"] else None,
            "临盘大小": m3["ou"][0] if m3["ou"] else None,
            "临盘大": m3["ou"][1] if m3["ou"] else None,
            "临盘小": m3["ou"][2] if m3["ou"] else None,
        }
        rows.append(row)

    if not rows:
        send(f"⚠️ `{ts}` 测试未抓到比赛")
        return

    # 生成 Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "快速测试"
    headers = list(rows[0].keys())
    ws.append(headers)
    for r in rows:
        ws.append([r.get(h) for h in headers])
    fname = f"nations_test_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    wb.save(fname)

    # 发送
    msg = f"🧪 *快速测试结果*\n🕒 `{ts}`\n共 {len(rows)} 场\n（第1次 vs 第3次）\n\n"
    for r in rows[:10]:
        msg += f"⚽ *{r['主队']} vs {r['客队']}* `{r['时间']}`\n"
        msg += f"开盘: {r['开盘主胜']} | {r['开盘平局']} | {r['开盘客胜']}\n"
        msg += f"临盘: {r['临盘主胜']} | {r['临盘平局']} | {r['临盘客胜']}\n\n"
    send(msg)
    send_file(fname, caption=f"快速测试 开盘vs临盘（共{len(rows)}场）")
    print("测试完成，已发送")

if __name__ == "__main__":
    main()
