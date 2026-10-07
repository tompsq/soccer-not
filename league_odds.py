import os, time, json, requests
from datetime import datetime, timedelta
from openpyxl import Workbook

T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")
HISTORY_FILE = "league_history.json"

LEAGUES = [
    ("英超", 1980), ("西甲", 2196), ("意甲", 2436), ("德甲", 1842),
    ("英冠", 1977), ("葡超", 2386), ("苏超", 2421), ("比甲", 1817),
    ("土超", 2592), ("欧冠", 2627), ("欧联", 2630),
]
MAX_PER_LEAGUE = 12

H = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Origin": "https://www.pinnacle.com",
    "Referer": "https://www.pinnacle.com/",
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
        time.sleep(1.5)
    except Exception as e:
        print("发送失败:", e)

def to_dec(a):
    try:
        a = float(a)
        return round(a / 100 + 1, 3) if a > 0 else round(100 / abs(a) + 1, 3)
    except:
        return None

def get(url):
    for _ in range(3):
        try:
            r = requests.get(url, headers=H, timeout=15)
            if r.status_code == 200:
                return r.json()
        except:
            time.sleep(1)
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

def is_saturday_close():
    now = datetime.utcnow()
    return now.weekday() == 4 and now.hour >= 17

def fetch_pinnacle(name, lid, only_upcoming_2h=False):
    ms = get(f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{lid}/matchups")
    if not ms:
        return []
    matches = {}
    now = datetime.utcnow() + timedelta(hours=8)
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
        if only_upcoming_2h:
            if not (now <= mt <= now + timedelta(hours=2)):
                continue
        else:
            if mt < now or mt > now + timedelta(days=10):
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
            "home": home,
            "away": away,
            "time": mt.strftime("%m-%d %H:%M"),
            "sort_time": mt.isoformat(),
            "1X2": {},
            "ah": None,
            "ou": None,
        }
    if not matches:
        return []

    mks = get(f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{lid}/markets/straight")
    if mks:
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
                        matches[mid]["ah"] = [line, to_dec(hp["price"]), to_dec(ap["price"])]
            elif t == "total":
                op = next((p for p in ps if p.get("designation") == "over"), None)
                up = next((p for p in ps if p.get("designation") == "under"), None)
                if op and up:
                    line = op.get("points", 0)
                    if matches[mid]["ou"] is None or abs(line - 2.5) < abs(matches[mid]["ou"][0] - 2.5):
                        matches[mid]["ou"] = [line, to_dec(op["price"]), to_dec(up["price"])]

    sorted_m = sorted(matches.values(), key=lambda x: x["sort_time"])
    return sorted_m if only_upcoming_2h else sorted_m[:MAX_PER_LEAGUE]

def main():
    mode = os.environ.get("RUN_MODE", "auto")
    only_upcoming_2h = (mode == "manual_upcoming")
    print(f"运行模式: {mode} | 只抓2小时: {only_upcoming_2h}")

    ts = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    history = load_history()
    current = {}
    all_rows = []

    for name, lid in LEAGUES:
        print(f"抓取 {name}...")
        rows = fetch_pinnacle(name, lid, only_upcoming_2h=only_upcoming_2h)
        print(f"  → {len(rows)} 场")
        for m in rows:
            key = f"{name}|{m['home']}|{m['away']}|{m['time']}"
            current[key] = m
            all_rows.append((name, m, key))
        time.sleep(0.5)

    if not all_rows:
        print("没有抓到数据")
        if only_upcoming_2h and T and C:
            try:
                requests.post(
                    f"https://api.telegram.org/bot{T}/sendMessage",
                    json={"chat_id": C, "text": f"⚠️ `{ts}` 未来2小时内没有可抓的比赛（可能已开赛/完场）。", "parse_mode": "Markdown"},
                    timeout=30,
                )
            except:
                pass
        return

    # 有历史就做对比（周六临盘 或 manual_upcoming）
    # 无历史则当早盘保存
    do_compare = bool(history)

    wb = Workbook()
    ws = wb.active

    if do_compare:
        ws.title = "早盘vs临盘"
        headers = [
            "联赛", "时间", "主队", "客队", "状态",
            "早_主胜", "早_平局", "早_客胜", "早_亚盘", "早_亚盘主", "早_亚盘客", "早_大小", "早_大球", "早_小球",
            "临_主胜", "临_平局", "临_客胜", "临_亚盘", "临_亚盘主", "临_亚盘客", "临_大小", "临_大球", "临_小球",
        ]
        ws.append(headers)
        for name, m, key in all_rows:
            early = history.get(key)
            c1 = m.get("1X2", {})
            cah = m.get("ah") or [None, None, None]
            cou = m.get("ou") or [None, None, None]
            if early:
                e1 = early.get("1X2", {})
                eah = early.get("ah") or [None, None, None]
                eou = early.get("ou") or [None, None, None]
                status = "可对比"
            else:
                e1, eah, eou = {}, [None, None, None], [None, None, None]
                status = "无早盘记录"
            ws.append([
                name, m["time"], m["home"], m["away"], status,
                e1.get("home"), e1.get("draw"), e1.get("away"),
                eah[0], eah[1], eah[2], eou[0], eou[1], eou[2],
                c1.get("home"), c1.get("draw"), c1.get("away"),
                cah[0], cah[1], cah[2], cou[0], cou[1], cou[2],
            ])
        fname = f"league_compare_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        caption = f"早盘 vs 临盘 对比 {ts}\n共 {len(all_rows)} 场（已开赛/完场可能不在列表）"
    else:
        ws.title = "早盘"
        headers = ["联赛", "时间", "主队", "客队", "主胜", "平局", "客胜", "亚盘", "亚盘主", "亚盘客", "大小", "大球", "小球"]
        ws.append(headers)
        for name, m, key in all_rows:
            c1 = m.get("1X2", {})
            cah = m.get("ah") or [None, None, None]
            cou = m.get("ou") or [None, None, None]
            ws.append([
                name, m["time"], m["home"], m["away"],
                c1.get("home"), c1.get("draw"), c1.get("away"),
                cah[0], cah[1], cah[2], cou[0], cou[1], cou[2],
            ])
        if not only_upcoming_2h:
            save_history(current)
            print("已保存早盘到 league_history.json")
        fname = f"league_odds_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        caption = f"各大联赛早盘 {ts}\n共 {len(all_rows)} 场"

    wb.save(fname)
    send_file(fname, caption=caption)
    print("已发送:", fname)

if __name__ == "__main__":
    main()
