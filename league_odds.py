import os, time, json, io, csv, requests
from datetime import datetime, timedelta
from collections import defaultdict
from openpyxl import Workbook
from openpyxl.styles import Font

T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")
HISTORY_FILE = "league_history.json"
CLEAR_OLD_CLOSE = os.environ.get("CLEAR_OLD_CLOSE", "").strip() == "1"

LEAGUES = [
    ("英超", 1980), ("西甲", 2196), ("意甲", 2436), ("德甲", 1842),
    ("英冠", 1977), ("葡超", 2386), ("苏超", 2421), ("比甲", 1817),
    ("荷甲", 1928), ("欧冠", 2627), ("欧联", 2630), ("法甲", 2036),
]

FORM_LEAGUES = [
    ("英超", "E0"), ("英冠", "E1"), ("西甲", "SP1"), ("意甲", "I1"),
    ("德甲", "D1"), ("法甲", "F1"), ("荷甲", "N1"), ("葡超", "P1"),
    ("苏超", "SC0"), ("比甲", "B1"),
]
FORM_SEASONS = ["2627", "2526"]
N_LAST = 6

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
    except Exception:
        return None

def get(url):
    for _ in range(3):
        try:
            r = requests.get(url, headers=H, timeout=15)
            if r.status_code == 200:
                return r.json()
        except Exception:
            time.sleep(1)
    return None

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
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

def clear_all_close(history):
    n = 0
    for k, v in history.items():
        if isinstance(v, dict) and v.get("close"):
            v["close"] = None
            n += 1
    print(f"已清空旧临盘: {n} 场")
    return history

def prune_history(history, grace_hours=3):
    valid = {name for name, _ in LEAGUES}
    cutoff = now_my() - timedelta(hours=grace_hours)
    drop = []
    for k, v in history.items():
        if not isinstance(v, dict):
            drop.append(k)
            continue
        league = v.get("league") or (k.split("|")[0] if "|" in k else "")
        if league not in valid:
            drop.append(k)
            continue
        ko = v.get("kickoff")
        if ko:
            try:
                kt = datetime.fromisoformat(ko)
                if kt < cutoff:
                    drop.append(k)
            except Exception:
                pass
    for k in drop:
        del history[k]
    print(f"已清理 history: 删除 {len(drop)} 场，剩余 {len(history)} 场")
    return history

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
        except Exception:
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

def filter_kickoff_within_hours(rows, hours=2, after_minutes=15):
    now = now_my()
    start = now - timedelta(minutes=after_minutes)
    end = now + timedelta(hours=hours)
    out = []
    for m in rows:
        ko = m.get("kickoff")
        if not ko:
            continue
        try:
            kt = datetime.fromisoformat(ko)
        except Exception:
            continue
        if start <= kt <= end:
            out.append(m)
    return out

def days_to_kick(kickoff_iso):
    try:
        kt = datetime.fromisoformat(kickoff_iso)
        return (kt.date() - now_my().date()).days
    except Exception:
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
    rec["league"] = league
    rec["home"] = m["home"]
    rec["away"] = m["away"]
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

def download_form_csv(season, code):
    url = f"https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        if r.status_code == 200 and "Date" in r.text[:800]:
            return r.text
    except Exception as e:
        print(f"form下载失败 {season}/{code}:", e)
    return None

def parse_form_matches(text):
    rows = list(csv.DictReader(io.StringIO(text)))
    out = []
    for row in rows:
        ds = (row.get("Date") or "").strip()
        home = (row.get("HomeTeam") or "").strip()
        away = (row.get("AwayTeam") or "").strip()
        try:
            hg, ag = int(row.get("FTHG")), int(row.get("FTAG"))
        except Exception:
            continue
        if not ds or not home or not away:
            continue
        dt = None
        for fmt in ("%d/%m/%y", "%d/%m/%Y"):
            try:
                dt = datetime.strptime(ds, fmt)
                break
            except Exception:
                pass
        if dt:
            out.append((dt, home, away, hg, ag))
    out.sort(key=lambda x: x[0])
    return out

def _one_form(lst, n=N_LAST):
    lst = sorted(lst, key=lambda x: x[0])[-n:]
    if not lst:
        return None
    pts = gf = ga = 0
    seq = []
    for _, _, g_f, g_a, p in lst:
        pts += p
        gf += g_f
        ga += g_a
        seq.append("W" if p == 3 else ("D" if p == 1 else "L"))
    return {"场次": len(lst), "积分": pts, "进球": gf, "失球": ga, "净胜": gf - ga, "战绩": "".join(seq)}

def build_forms_from_matches(matches):
    by = defaultdict(list)
    for dt, home, away, hg, ag in matches:
        hp, ap = (3, 0) if hg > ag else ((1, 1) if hg == ag else (0, 3))
        by[home].append((dt, True, hg, ag, hp))
        by[away].append((dt, False, ag, hg, ap))
    res = {}
    for team, lst in by.items():
        res[team] = {
            "all": _one_form(lst),
            "home": _one_form([x for x in lst if x[1]]),
            "away": _one_form([x for x in lst if not x[1]]),
        }
    return res

def fetch_all_forms():
    today = now_my().replace(hour=0, minute=0, second=0, microsecond=0)
    all_rows = []
    for cn, code in FORM_LEAGUES:
        text = None
        for season in FORM_SEASONS:
            text = download_form_csv(season, code)
            if text:
                print(f"form {cn}: 赛季 {season}")
                break
        if not text:
            print(f"form {cn}: 无CSV")
            continue
        matches = [m for m in parse_form_matches(text) if m[0] < today]
        forms = build_forms_from_matches(matches)
        for team in sorted(forms.keys()):
            a, h, aw = forms[team]["all"], forms[team]["home"], forms[team]["away"]
            all_rows.append([
                cn, team,
                a["场次"] if a else 0,
                a["积分"] if a else None, a["进球"] if a else None, a["失球"] if a else None,
                a["净胜"] if a else None, a["战绩"] if a else "",
                h["积分"] if h else None, h["进球"] if h else None, h["失球"] if h else None, h["战绩"] if h else "",
                aw["积分"] if aw else None, aw["进球"] if aw else None, aw["失球"] if aw else None, aw["战绩"] if aw else "",
            ])
        time.sleep(0.5)
    return all_rows

def add_form_sheet(wb):
    rows = fetch_all_forms()
    ws = wb.create_sheet("近6场状态")
    ws.append([f"近{N_LAST}场纯联赛 | {now_my().strftime('%Y-%m-%d %H:%M')} | football-data.co.uk"])
    ws.append([])
    headers = [
        "联赛", "球队", "近6场次", "近6积分", "近6进球", "近6失球", "近6净胜", "近6战绩",
        "主场近6积分", "主场近6进球", "主场近6失球", "主场近6战绩",
        "客场近6积分", "客场近6进球", "客场近6失球", "客场近6战绩",
    ]
    ws.append(headers)
    for r in rows:
        ws.append(r)
    print(f"已写入近6场: {len(rows)} 队")

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

def build_workbook(history, close_ts=None):
    wb = Workbook()

    # 早盘
    ws = wb.active
    ws.title = "早盘"
    items = [(k, v) for k, v in history.items() if isinstance(v, dict) and v.get("early")]
    items.sort(key=lambda x: (x[1].get("league", ""), x[1].get("kickoff") or ""))
    early_dates = sorted({v["early"].get("ts", "")[:10] for _, v in items if v.get("early")})
    note = "早盘：首次入库(仅亚盘+大小) | 记录日期: " + (", ".join(early_dates) if early_dates else "无")
    sheet_note(ws, ["联赛", "时间", "主队", "客队", "记录时间"] + ODDS_HEADERS, note)
    for _, v in items:
        e = v["early"]
        ws.append([v.get("league"), v.get("time"), v.get("home"), v.get("away"), e.get("ts")] + row_odds(e))

    # 临盘
    ws3 = wb.create_sheet("临盘")
    items3 = [(k, v) for k, v in history.items() if isinstance(v, dict) and v.get("close")]
    if close_ts:
        items3 = [(k, v) for k, v in items3 if (v.get("close") or {}).get("ts") == close_ts]
    items3.sort(key=lambda x: (x[1].get("league", ""), x[1].get("kickoff") or ""))
    close_dates = sorted({v["close"].get("ts", "")[:10] for _, v in items3 if v.get("close")})
    note3 = "临盘：未来2h(含开赛后15m) 仅亚盘+大小 | " + (", ".join(close_dates) if close_dates else "无")
    sheet_note(ws3, ["联赛", "时间", "主队", "客队", "抓取时间"] + ODDS_HEADERS, note3)
    for _, v in items3:
        e = v["close"]
        ws3.append([v.get("league"), v.get("time"), v.get("home"), v.get("away"), e.get("ts")] + row_odds(e))

    # 对比：必须同时有 early 和 close
    ws4 = wb.create_sheet("对比")
    both = [
        v for v in history.values()
        if isinstance(v, dict) and v.get("early") and v.get("close")
    ]
    both.sort(key=lambda v: (v.get("league", ""), v.get("kickoff") or ""))
    note4 = f"仅含早盘+临盘齐全的场 | 导出 {now_my().strftime('%Y-%m-%d %H:%M')}"
    sheet_note(
        ws4,
        ["联赛", "时间", "主队", "客队",
         "早_抓取"] + [f"早_{h}" for h in ODDS_HEADERS] +
        ["临_抓取"] + [f"临_{h}" for h in ODDS_HEADERS],
        note4,
    )
    for v in both:
        e, c = v["early"], v["close"]
        ws4.append(
            [v.get("league"), v.get("time"), v.get("home"), v.get("away"),
             e.get("ts")] + row_odds(e) +
            [c.get("ts")] + row_odds(c)
        )
    return wb

def resolve_mode():
    mode = os.environ.get("RUN_MODE", "auto").strip().lower()
    if mode in ("close", "manual_close"):
        return "close"
    if mode in ("early", "scan", "mid", "auto", "thursday"):
        return "scan"   # mid 一律当 scan
    return "scan"

def main():
    mode = resolve_mode()
    ts = now_my().strftime("%Y-%m-%d %H:%M:%S")
    print(f"模式: {mode} | 时间: {ts} | CLEAR_OLD_CLOSE={CLEAR_OLD_CLOSE}")

    history = load_history()
    for k, v in history.items():
        if isinstance(v, dict) and not v.get("league") and "|" in k:
            v["league"] = k.split("|")[0]

    history = prune_history(history, grace_hours=3)

    if CLEAR_OLD_CLOSE:
        history = clear_all_close(history)

    save_history(history)

    n_new_early = 0
    n_mid = 0
    n_close = 0

    for name, lid in LEAGUES:
        print(f"抓取 {name}...")
        days = 2 if mode == "close" else 16
        rows = fetch_pinnacle(name, lid, days_ahead=days)
        if mode == "close":
            rows = filter_kickoff_within_hours(rows, hours=2, after_minutes=15)
            print(f"  → 临盘窗口 {len(rows)} 场")
        else:
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

    wb = build_workbook(history, close_ts=ts if mode == "close" else None)
    if mode == "close":
        try:
            add_form_sheet(wb)
        except Exception as e:
            print("近6场附带失败:", e)

    fname = f"league_odds_{mode}_{now_my().strftime('%Y%m%d_%H%M')}.xlsx"
    wb.save(fname)

    if mode == "close":
        caption = f"临盘+近6场 | {ts}\n临盘更新 {n_close} 场 | history {len(history)} 场"
    else:
        caption = f"盘口 {mode} | {ts}\nhistory {len(history)} 场 | 新早{n_new_early} 临{n_close}"
    send_file(fname, caption=caption)
    print("已保存并尝试发送:", fname)

if __name__ == "__main__":
    main()
