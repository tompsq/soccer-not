import os, time, json, requests
from datetime import datetime, timedelta
from openpyxl import Workbook
from openpyxl.styles import Font

T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")
HISTORY_FILE = "league_history.json"

LEAGUES = [
    ("英超", 1980), ("西甲", 2196), ("意甲", 2436), ("德甲", 1842),
    ("英冠", 1977), ("葡超", 2386), ("苏超", 2421), ("比甲", 1817),
    ("土超", 2592), ("欧冠", 2627), ("欧联", 2630), ("法甲", 2036),
]

H = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Origin": "https://www.pinnacle.com",
    "Referer": "https://www.pinnacle.com/",
}

def now_my():
    return datetime.utcnow() + timedelta(hours=8)

def send_file(path, caption=""):
    if not T or not C:
        print("跳过TG: 缺少 token/chat_id | 文件:", path)
        return
    try:
        with open(path, "rb") as f:
            r = requests.post(
                f"https://api.telegram.org/bot{T}/sendDocument",
                data={"chat_id": C, "caption": (caption or "")[:1000]},
                files={"document": f},
                timeout=60,
            )
        print("TG:", r.status_code, r.text[:200])
        time.sleep(1.2)
    except Exception as e:
        print("发送异常:", e)

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

def make_key(league, home, away):
    return f"{league}|{home.strip().lower()}|{away.strip().lower()}"

def snap_from_match(m, ts):
    return {
        "ts": ts,
        "time": m.get("time"),
        "1X2": m.get("1X2") or {},
        "ah": m.get("ah"),
        "ou": m.get("ou"),
    }

def fetch_pinnacle(name, lid, days_ahead=16):
    ms = get(f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{lid}/matchups")
    if not ms:
        return []
    matches = {}
    now = now_my()
    end = now + timedelta(days=days_ahead)
    for m in ms:
        if m.get("type") != "matchup":
            continue
        st = m.get("startTime") or ""
        if not st:
            continue
        try:
            mt = datetime.strptime(st[:19], "%Y-%m-%dT%H:%M:%S") + timedelta(hours=8)
        except:
            continue
        if mt < now or mt > end:
            continue
        ps = m.get("participants") or []
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
            "kickoff": mt.isoformat(timespec="minutes"),
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
            ps = mk.get("prices") or []
            if t == "moneyline":
                for p in ps:
                    d = p.get("designation")
                    if d in ("home", "draw", "away"):
                        matches[mid]["1X2"][d] = to_dec(p.get("price"))
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
    return sorted(matches.values(), key=lambda x: x["sort_time"])

def days_to_kick(kickoff_iso):
    try:
        kt = datetime.fromisoformat(kickoff_iso)
        return (kt.date() - now_my().date()).days
    except:
        return 999

def update_history(history, league, m, mode, ts):
    key = make_key(league, m["home"], m["away"])
    rec = history.get(key) or {
        "league": league,
        "home": m["home"],
        "away": m["away"],
        "kickoff": m.get("kickoff"),
        "time": m.get("time"),
        "early": None,
        "mid": None,
        "close": None,
    }
    rec["kickoff"] = m.get("kickoff") or rec.get("kickoff")
    rec["time"] = m.get("time") or rec.get("time")
    snap = snap_from_match(m, ts)

    if mode == "scan":
        if not rec.get("early"):
            rec["early"] = snap
    elif mode == "mid":
        if not rec.get("early"):
            rec["early"] = snap
        d = days_to_kick(rec.get("kickoff") or m.get("kickoff"))
        if 2 <= d <= 5:
            rec["mid"] = snap
    elif mode == "close":
        if not rec.get("early"):
            rec["early"] = snap
        rec["close"] = snap

    history[key] = rec
    return history

def sheet_note(ws, headers, note):
    ws.append([note])
    ws["A1"].font = Font(bold=True, color="0000AA")
    ws.append([])
    ws.append(headers)

def row_odds(snap):
    if not snap:
        return [None] * 9
    x = snap.get("1X2") or {}
    ah = snap.get("ah") or [None, None, None]
    ou = snap.get("ou") or [None, None, None]
    return [
        x.get("home"), x.get("draw"), x.get("away"),
        ah[0], ah[1], ah[2],
        ou[0], ou[1], ou[2],
    ]

ODDS_HEADERS = ["主胜", "平局", "客胜", "亚盘", "亚盘主", "亚盘客", "大小", "大球", "小球"]

def build_workbook(history):
    wb = Workbook()

    ws = wb.active
    ws.title = "早盘"
    items = [(k, v) for k, v in history.items() if v.get("early")]
    items.sort(key=lambda x: (x[1].get("league", ""), x[1].get("kickoff") or ""))
    early_dates = sorted({v["early"].get("ts", "")[:10] for _, v in items if v.get("early")})
    note = "早盘：各场首次入库赔率 | 记录日期: " + (", ".join(early_dates) if early_dates else "无")
    sheet_note(ws, ["联赛", "时间", "主队", "客队", "记录时间"] + ODDS_HEADERS, note)
    for _, v in items:
        e = v["early"]
        ws.append([v.get("league"), v.get("time"), v.get("home"), v.get("away"), e.get("ts")] + row_odds(e))

    ws2 = wb.create_sheet("中盘")
    items2 = [(k, v) for k, v in history.items() if v.get("mid")]
    items2.sort(key=lambda x: (x[1].get("league", ""), x[1].get("kickoff") or ""))
    mid_dates = sorted({v["mid"].get("ts", "")[:10] for _, v in items2 if v.get("mid")})
    note2 = "中盘：开赛前约2\~5天（周四任务）| 抓取日期: " + (", ".join(mid_dates) if mid_dates else "无")
    sheet_note(ws2, ["联赛", "时间", "主队", "客队", "抓取时间"] + ODDS_HEADERS, note2)
    for _, v in items2:
        e = v["mid"]
        ws2.append([v.get("league"), v.get("time"), v.get("home"), v.get("away"), e.get("ts")] + row_odds(e))

    ws3 = wb.create_sheet("临盘")
    items3 = [(k, v) for k, v in history.items() if v.get("close")]
    items3.sort(key=lambda x: (x[1].get("league", ""), x[1].get("kickoff") or ""))
    close_dates = sorted({v["close"].get("ts", "")[:10] for _, v in items3 if v.get("close")})
    note3 = "临盘：手动 RUN_MODE=close | 抓取日期: " + (", ".join(close_dates) if close_dates else "无")
    sheet_note(ws3, ["联赛", "时间", "主队", "客队", "抓取时间"] + ODDS_HEADERS, note3)
    for _, v in items3:
        e = v["close"]
        ws3.append([v.get("league"), v.get("time"), v.get("home"), v.get("away"), e.get("ts")] + row_odds(e))

    ws4 = wb.create_sheet("对比")
    all_items = sorted(history.values(), key=lambda v: (v.get("league", ""), v.get("kickoff") or ""))
    note4 = f"导出时间: {now_my().strftime('%Y-%m-%d %H:%M')} | 早=首次 中=赛前2\~5天 临=manual"
    sheet_note(
        ws4,
        ["联赛", "时间", "主队", "客队",
         "早_抓取"] + [f"早_{h}" for h in ODDS_HEADERS] +
        ["中_抓取"] + [f"中_{h}" for h in ODDS_HEADERS] +
        ["临_抓取"] + [f"临_{h}" for h in ODDS_HEADERS],
        note4,
    )
    for v in all_items:
        if not (v.get("early") or v.get("mid") or v.get("close")):
            continue
        e, m, c = v.get("early") or {}, v.get("mid") or {}, v.get("close") or {}
        ws4.append(
            [v.get("league"), v.get("time"), v.get("home"), v.get("away"),
             e.get("ts")] + row_odds(v.get("early")) +
            [m.get("ts")] + row_odds(v.get("mid")) +
            [c.get("ts")] + row_odds(v.get("close"))
        )
    return wb

def resolve_mode():
    mode = os.environ.get("RUN_MODE", "auto").strip().lower()
    if mode in ("close", "manual_close"):
        return "close"
    if mode in ("mid", "thursday"):
        return "mid"
    if mode in ("early", "scan"):
        return "scan"
    now = datetime.utcnow()
    if now.weekday() == 3:
        return "mid"
    return "scan"

def main():
    mode = resolve_mode()
    ts = now_my().strftime("%Y-%m-%d %H:%M:%S")
    print(f"模式: {mode} | 时间: {ts}")

    history = load_history()
    n_new_early = n_mid = n_close = 0

    for name, lid in LEAGUES:
        print(f"抓取 {name}...")
        rows = fetch_pinnacle(name, lid, days_ahead=16)
        print(f"  → {len(rows)} 场")
        for m in rows:
            key = make_key(name, m["home"], m["away"])
            before = history.get(key) or {}
            update_history(history, name, m, mode, ts)
            after = history[key]
            if mode == "scan" and after.get("early") and not before.get("early"):
                n_new_early += 1
            if mode == "mid" and after.get("mid"):
                if not before.get("mid") or before["mid"].get("ts") != ts:
                    n_mid += 1
            if mode == "close" and after.get("close"):
                n_close += 1
        time.sleep(0.4)

    save_history(history)
    print(f"history 场次: {len(history)} | 新早盘 {n_new_early} | 中盘更新 {n_mid} | 临盘更新 {n_close}")

    wb = build_workbook(history)
    fname = f"league_odds_{mode}_{now_my().strftime('%Y%m%d_%H%M')}.xlsx"
    wb.save(fname)
    send_file(
        fname,
        caption=f"盘口 {mode} | {ts}\nhistory {len(history)} 场 | 新早{n_new_early} 中{n_mid} 临{n_close}",
    )
    print("已保存并尝试发送:", fname)

if __name__ == "__main__":
    main()
