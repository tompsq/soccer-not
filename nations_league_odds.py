import os, time, requests, json
from datetime import datetime, timedelta
from openpyxl import Workbook

T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")
HISTORY_FILE = "nations_history.json"

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

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_history(data):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
def fetch_matches():
    now_my = datetime.utcnow() + timedelta(hours=8)
    t_start = now_my
    t_end = now_my + timedelta(hours=36)
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
            matches[str(m["id"])] = {
                "id": str(m["id"]),
                "league": name,
                "home": home,
                "away": away,
                "time": mt.strftime("%m-%d %H:%M"),
                "kickoff": mt.isoformat(),
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
            mid = str(mk.get("matchupId"))
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
                        matches[mid]["ah"] = [line, to_dec(hp["price"]), to_dec(ap["price"])]
            elif t == "total":
                op = next((p for p in ps if p.get("designation") == "over"), None)
                up = next((p for p in ps if p.get("designation") == "under"), None)
                if op and up:
                    line = op.get("points", 0)
                    if matches[mid]["ou"] is None or abs(line - 2.5) < abs(matches[mid]["ou"][0] - 2.5):
                        matches[mid]["ou"] = [line, to_dec(op["price"]), to_dec(up["price"])]
        all_matches.update(matches)
        time.sleep(0.5)
    return all_matches

def main():
    now_my = datetime.utcnow() + timedelta(hours=8)
    ts = now_my.strftime("%Y-%m-%d %H:%M:%S")
    hour = now_my.hour
    print(f"当前大马时间：{ts}")

    history = load_history()
    current = fetch_matches()
    print(f"本次抓到 {len(current)} 场")

    for mid, m in current.items():
        if mid not in history:
            history[mid] = {
                "league": m["league"],
                "home": m["home"],
                "away": m["away"],
                "time": m["time"],
                "kickoff": m["kickoff"],
                "open_1x2": m["1X2"],
                "open_ah": m["ah"],
                "open_ou": m["ou"],
                "curr_1x2": m["1X2"],
                "curr_ah": m["ah"],
                "curr_ou": m["ou"],
                "first_seen": ts,
                "last_seen": ts,
            }
        else:
            history[mid]["curr_1x2"] = m["1X2"]
            history[mid]["curr_ah"] = m["ah"]
            history[mid]["curr_ou"] = m["ou"]
            history[mid]["last_seen"] = ts
            history[mid]["time"] = m["time"]

    # 清理过期比赛
    cleaned = {}
    for mid, h in history.items():
        try:
            ko = datetime.fromisoformat(h["kickoff"])
            if ko > now_my - timedelta(hours=6):
                cleaned[mid] = h
        except:
            cleaned[mid] = h
    history = cleaned
    save_history(history)
    print(f"历史记录保存完成，共 {len(history)} 场")

    # 只有晚上 22 点后才发送
    if hour < 22:
        print("非发送时段，只更新历史")
        return

    rows = []
    for mid, h in history.items():
        row = {
            "联赛": h["league"],
            "时间": h["time"],
            "主队": h["home"],
            "客队": h["away"],
            "开盘主胜": h["open_1x2"].get("home"),
            "开盘平局": h["open_1x2"].get("draw"),
            "开盘客胜": h["open_1x2"].get("away"),
            "临盘主胜": h["curr_1x2"].get("home"),
            "临盘平局": h["curr_1x2"].get("draw"),
            "临盘客胜": h["curr_1x2"].get("away"),
            "开盘亚盘": h["open_ah"][0] if h["open_ah"] else None,
            "开盘亚盘主": h["open_ah"][1] if h["open_ah"] else None,
            "开盘亚盘客": h["open_ah"][2] if h["open_ah"] else None,
            "临盘亚盘": h["curr_ah"][0] if h["curr_ah"] else None,
            "临盘亚盘主": h["curr_ah"][1] if h["curr_ah"] else None,
            "临盘亚盘客": h["curr_ah"][2] if h["curr_ah"] else None,
            "开盘大小": h["open_ou"][0] if h["open_ou"] else None,
            "开盘大": h["open_ou"][1] if h["open_ou"] else None,
            "开盘小": h["open_ou"][2] if h["open_ou"] else None,
            "临盘大小": h["curr_ou"][0] if h["curr_ou"] else None,
            "临盘大": h["curr_ou"][1] if h["curr_ou"] else None,
            "临盘小": h["curr_ou"][2] if h["curr_ou"] else None,
        }
        rows.append(row)

    if not rows:
        send(f"⚠️ `{ts}` 没有可发送的比赛")
        return

    wb = Workbook()
    ws = wb.active
    ws.title = "开盘vs临盘"
    headers = list(rows[0].keys())
    ws.append(headers)
    for r in rows:
        ws.append([r.get(h) for h in headers])
    fname = f"nations_open_close_{now_my.strftime('%Y%m%d_%H%M')}.xlsx"
    wb.save(fname)

    msg = f"📅 *欧国联 开盘 vs 临盘*\n🕒 `{ts}`\n共 {len(rows)} 场\n\n"
    for r in rows[:12]:
        msg += f"⚽ *{r['主队']} vs {r['客队']}* `{r['时间']}`\n"
        msg += f"开盘: {r['开盘主胜']} | {r['开盘平局']} | {r['开盘客胜']}\n"
        msg += f"临盘: {r['临盘主胜']} | {r['临盘平局']} | {r['临盘客胜']}\n\n"
    send(msg)
    send_file(fname, caption=f"欧国联 开盘vs临盘（共{len(rows)}场）")
    print("已发送报告")

if __name__ == "__main__":
    main()
