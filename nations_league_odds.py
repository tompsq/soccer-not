import os, time, requests
from datetime import datetime, timedelta
from openpyxl import Workbook

T, C = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")
LEAGUES = [("欧国联A",200719),("欧国联B",200721),("欧国联C",200726),("欧国联D",200727)]
H = {"User-Agent":"Mozilla/5.0","Accept":"application/json","Origin":"https://www.pinnacle.com","Referer":"https://www.pinnacle.com/"}

def send(t):
    if not T or not C: print(t); return
    try:
        requests.post(f"https://api.telegram.org/bot{T}/sendMessage",
                      json={"chat_id":C,"text":t[:4000],"parse_mode":"Markdown"}, timeout=30)
        time.sleep(1.2)
    except Exception as e: print(e)

def send_file(path, caption=""):
    if not T or not C: print("文件已生成:", path); return
    try:
        with open(path, "rb") as f:
            requests.post(f"https://api.telegram.org/bot{T}/sendDocument",
                          data={"chat_id":C,"caption":caption}, files={"document":f}, timeout=60)
        time.sleep(1.5)
    except Exception as e: print("发送文件失败:", e)

def to_dec(a):
    try:
        a = float(a)
        return round(a/100+1,3) if a>0 else round(100/abs(a)+1,3)
    except: return None

def get(url):
    for _ in range(3):
        try:
            r = requests.get(url, headers=H, timeout=20)
            if r.status_code == 200: return r.json()
        except: time.sleep(1.5)
    return None

def fetch(name, lid, t_start, t_end):
    ms = get(f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{lid}/matchups")
    if not ms: return []
    matches = {}
    for m in ms:
        if m.get("type") != "matchup": continue
        st = m.get("startTime","")
        if not st: continue
        try: mt = datetime.strptime(st[:19], "%Y-%m-%dT%H:%M:%S") + timedelta(hours=8)
        except: continue
        if not (t_start <= mt <= t_end): continue
        ps = m.get("participants",[])
        if len(ps) < 2: continue
        home = next((p["name"] for p in ps if p.get("alignment")=="home"), None)
        away = next((p["name"] for p in ps if p.get("alignment")=="away"), None)
        if not home or not away: continue
        if "(" in home or "(" in away: continue
        matches[m["id"]] = {
            "home": home, "away": away,
            "time": mt.strftime("%m-%d %H:%M"),
            "1X2": {}, "ah": None, "ou": None
        }
    if not matches: return []

    mks = get(f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{lid}/markets/straight")
    if not mks: return []

    for mk in mks:
        mid = mk.get("matchupId")
        if mid not in matches or mk.get("period") != 0 or mk.get("isAlternate") is True:
            continue
        t, ps = mk.get("type"), mk.get("prices",[])
        if t == "moneyline":
            for p in ps:
                d = p.get("designation")
                if d in ("home","draw","away"):
                    matches[mid]["1X2"][d] = to_dec(p["price"])
        elif t == "spread":
            hp = next((p for p in ps if p.get("designation")=="home"), None)
            ap = next((p for p in ps if p.get("designation")=="away"), None)
            if hp and ap:
                line = hp.get("points",0)
                if matches[mid]["ah"] is None or abs(line) < abs(matches[mid]["ah"][0]):
                    matches[mid]["ah"] = (line, to_dec(hp["price"]), to_dec(ap["price"]))
        elif t == "total":
            op = next((p for p in ps if p.get("designation")=="over"), None)
            up = next((p for p in ps if p.get("designation")=="under"), None)
            if op and up:
                line = op.get("points",0)
                if matches[mid]["ou"] is None or abs(line-2.5) < abs(matches[mid]["ou"][0]-2.5):
                    matches[mid]["ou"] = (line, to_dec(op["price"]), to_dec(up["price"]))
    return sorted(matches.values(), key=lambda x: x["time"])
def main():
    now_my = datetime.utcnow() + timedelta(hours=8)
    tomorrow = now_my.date() + timedelta(days=1)
    t_start = datetime.combine(tomorrow, datetime.min.time())
    t_end = datetime.combine(tomorrow, datetime.max.time())
    ts = now_my.strftime("%Y-%m-%d %H:%M:%S")
    print(f"当前马来西亚时间：{ts}")
    print(f"抓取窗口：{t_start.strftime('%Y-%m-%d %H:%M')} \~ {t_end.strftime('%Y-%m-%d %H:%M')}")

    all_rows = []
    all_msg = []

    for name, lid in LEAGUES:
        rows = fetch(name, lid, t_start, t_end)
        print(f"{name}: {len(rows)} 场")
        if not rows: continue

        lines = [f"🏆 *【{name}】* （{len(rows)} 场）"]
        for m in rows:
            row = {
                "联赛": name,
                "时间": m["time"],
                "主队": m["home"],
                "客队": m["away"],
                "主胜": m["1X2"].get("home"),
                "平局": m["1X2"].get("draw"),
                "客胜": m["1X2"].get("away"),
                "亚盘": None, "亚盘主": None, "亚盘客": None,
                "大小": None, "大球": None, "小球": None
            }
            s = f"⚽ *{m['home']} vs {m['away']}* 🕒 `{m['time']}`"
            if len(m["1X2"]) >= 3:
                s += f"\n   🔹 `1X2` : {m['1X2']['home']} | {m['1X2']['draw']} | {m['1X2']['away']}"
            if m["ah"]:
                line, ho, ao = m["ah"]
                ls = f"{line:+g}" if line != 0 else "0"
                s += f"\n   🔹 `亚盘` : 主{ls} {ho} | 客 {ao}"
                row["亚盘"] = line
                row["亚盘主"] = ho
                row["亚盘客"] = ao
            if m["ou"]:
                line, oo, uo = m["ou"]
                s += f"\n   🔹 `大小` : {line} 大{oo} | 小{uo}"
                row["大小"] = line
                row["大球"] = oo
                row["小球"] = uo
            lines.append(s)
            all_rows.append(row)
        all_msg.append("\n\n".join(lines))
        time.sleep(0.8)

    if not all_rows:
        send(f"⚠️ `{ts}` 明天（{tomorrow.strftime('%Y-%m-%d')}）没有欧国联比赛。")
        return

    # 生成 Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "明天欧国联"
    headers = ["联赛","时间","主队","客队","主胜","平局","客胜","亚盘","亚盘主","亚盘客","大小","大球","小球"]
    ws.append(headers)
    for r in all_rows:
        ws.append([r.get(h) for h in headers])
    fname = f"nations_league_tomorrow_{tomorrow.strftime('%Y%m%d')}.xlsx"
    wb.save(fname)

    # 发送文字
    chunks, cur = [], ""
    for block in all_msg:
        if len(cur) + len(block) + 4 > 3800:
            chunks.append(cur)
            cur = block
        else:
            cur += ("\n\n" if cur else "") + block
    if cur: chunks.append(cur)

    total = len(chunks)
    for idx, ch in enumerate(chunks, 1):
        title = f"📅 *【明天 ({tomorrow.strftime('%Y-%m-%d')}) 欧国联"
        if total > 1: title += f" ({idx}/{total})"
        title += f"】*\n🕒 `{ts}`\n\n"
        send(title + ch)

    # 发送 Excel
    send_file(fname, caption=f"明天欧国联盘口 {tomorrow.strftime('%Y-%m-%d')}（共{len(all_rows)}场）")
    print("Excel 已生成并发送:", fname)

if __name__ == "__main__":
    main()
