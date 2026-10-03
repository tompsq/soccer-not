import os, time, requests, json
from datetime import datetime, timedelta
from openpyxl import Workbook

# ================= 1. 基础配置与环境变量 =================
T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")
HISTORY_FILE = "nations_history.json"
XG_FILE = "xg_data.json"

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

# ================= 自动初始化与加载本地缓存 =================
def load_history():
    if not os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("初始化 nations_history.json 失败:", e)
        return {}
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_history(data):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_xg_data():
    if not os.path.exists(XG_FILE):
        default_xg = {
            "示例国家队": {"matches": 0, "xG_for": 0.0, "xG_against": 0.0}
        }
        try:
            with open(XG_FILE, "w", encoding="utf-8") as f:
                json.dump(default_xg, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("初始化 xg_data.json 失败:", e)
        return default_xg
    try:
        with open(XG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}
# ================= 2. 赔率抓取核心逻辑 =================
def fetch(name, lid, t_start, t_end):
    ms = get(f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{lid}/matchups")
    if not ms:
        return []
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
            "kickoff": mt.isoformat(),
            "1X2": {},
            "ah": None,
            "ou": None,
        }
    if not matches:
        return []

    mks = get(f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{lid}/markets/straight")
    if not mks:
        return []

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
    return list(matches.values())
["away"],
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
        # ================= 3. 主调度与 Excel 整合发送逻辑（已集成 xG + 伤停） =================
def load_injuries_data():
    inj_file = "injuries_data.json"
    if not os.path.exists(inj_file):
        default_inj = {
            "示例国家队": {"missing_players": "无重大伤停", "impact": "低"}
        }
        try:
            with open(inj_file, "w", encoding="utf-8") as f:
                json.dump(default_inj, f, ensure_ascii=False, indent=2)
        except:
            pass
        return default_inj
    try:
        with open(inj_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def main():
    now_my = datetime.utcnow() + timedelta(hours=8)
    tomorrow = now_my.date() + timedelta(days=1)
    t_start = datetime.combine(tomorrow, datetime.min.time())
    t_end = datetime.combine(tomorrow, datetime.max.time())
    ts = now_my.strftime("%Y-%m-%d %H:%M:%S")
    hour = now_my.hour

    print(f"当前大马时间：{ts}  小时={hour}")
    history = load_history()

    current_matches = []
    for name, lid in LEAGUES:
        rows = fetch(name, lid, t_start, t_end)
        print(f"{name}: {len(rows)} 场")
        current_matches.extend(rows)
        time.sleep(0.6)

    for m in current_matches:
        mid = m["id"]
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

    save_history(history)
    print(f"历史记录已更新，共 {len(history)} 场")

    if hour < 23:
        print("非最终运行，只更新历史，不发送")
        return

    rows = []
    for mid, h in history.items():
        try:
            ko = datetime.fromisoformat(h["kickoff"])
            if ko.date() != tomorrow:
                continue
        except:
            continue

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
        send(f"⚠️ `{ts}` 明天没有可发送的欧国联比赛")
        return

    # ================= 生成多 Sheet 综合 Excel =================
    wb = Workbook()
    
    # Sheet 1: 赔率开盘 vs 临盘
    ws1 = wb.active
    ws1.title = "开盘vs临盘"
    headers = list(rows[0].keys())
    ws1.append(headers)
    for r in rows:
        ws1.append([r.get(h) for h in headers])

    # Sheet 2: 球队 xG 数据缓存
    ws2 = wb.create_sheet(title="球队xG数据")
    ws2.append(["球队", "场次", "场均预期进球(xG)", "场均预期失球(xGA)"])
    xg_cache = load_xg_data()
    if xg_cache:
        for team, val in xg_cache.items():
            ws2.append([team, val.get("matches", 0), val.get("xG_for", 0), val.get("xG_against", 0)])

    # Sheet 3: 伤停情报缓存
    ws3 = wb.create_sheet(title="核心伤停情报")
    ws3.append(["球队", "关键伤停球员 / 停赛", "阵容影响评估"])
    inj_cache = load_injuries_data()
    if inj_cache:
        for team, val in inj_cache.items():
            ws3.append([team, val.get("missing_players", ""), val.get("impact", "")])

    fname = f"nations_open_close_{tomorrow.strftime('%Y%m%d')}.xlsx"
    wb.save(fname)

    # 推送 Telegram 文本摘要
    msg = f"📅 *【明天 ({tomorrow.strftime('%Y-%m-%d')}) 欧国联 综合情报】*\n🕒 `{ts}`\n共 {len(rows)} 场\n\n"
    for r in rows[:15]:
        msg += f"⚽ *{r['主队']} vs {r['客队']}* `{r['时间']}`\n"
        msg += f"   开盘 1X2: {r['开盘主胜']} | {r['开盘平局']} | {r['开盘客胜']}\n"
        msg += f"   临盘 1X2: {r['临盘主胜']} | {r['临盘平局']} | {r['临盘客胜']}\n\n"
    send(msg)

    # 推送双 Sheet 打包好的 Excel 文件
    send_file(fname, caption=f"欧国联 赔率与xG综合报表 {tomorrow.strftime('%Y-%m-%d')}（共{len(rows)}场）")
    print("最终报告已发送")

if __name__ == "__main__":
    main()
