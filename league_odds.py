import os, time, requests
from datetime import datetime, timedelta
from openpyxl import Workbook

T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")

LEAGUES = [
    ("英超", 1980),
    ("西甲", 2196),
    ("意甲", 2436),
    ("德甲", 1842),
    ("英冠", 1977),
    ("葡超", 2386),
    ("苏超", 2421),
    ("比甲", 1817),
    ("土超", 2592),
    ("欧冠", 2627),
    ("欧联", 2630),
]

MAX_PER_LEAGUE = 12

H = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Origin": "https://www.pinnacle.com",
    "Referer": "https://www.pinnacle.com/",
}

SH = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Referer": "https://www.sofascore.com/",
    "Origin": "https://www.sofascore.com",
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
        print("发送文件失败:", e)

def to_dec(a):
    try:
        a = float(a)
        return round(a / 100 + 1, 3) if a > 0 else round(100 / abs(a) + 1, 3)
    except:
        return None

def sofascore_get(url):
    try:
        r = requests.get(url, headers=SH, timeout=12)
        if r.status_code == 200:
            return r.json()
        print(f"Sofascore {r.status_code}: {url[:80]}")
    except Exception as e:
        print(f"Sofascore 错误: {e}")
    return None
def sofascore_get(url):
    try:
        r = requests.get(url, headers=SH, timeout=12)
        if r.status_code == 200:
            return r.json()
        print(f"Sofascore {r.status_code}: {url[:80]}")
    except Exception as e:
        print(f"Sofascore 错误: {e}")
    return None

def fetch_pinnacle(name, lid):
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
            "home": home,
            "away": away,
            "time": mt.strftime("%m-%d %H:%M"),
            "sort_time": mt,
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
                        matches[mid]["ah"] = (line, to_dec(hp["price"]), to_dec(ap["price"]))
            elif t == "total":
                op = next((p for p in ps if p.get("designation") == "over"), None)
                up = next((p for p in ps if p.get("designation") == "under"), None)
                if op and up:
                    line = op.get("points", 0)
                    if matches[mid]["ou"] is None or abs(line - 2.5) < abs(matches[mid]["ou"][0] - 2.5):
                        matches[mid]["ou"] = (line, to_dec(op["price"]), to_dec(up["price"]))

    sorted_m = sorted(matches.values(), key=lambda x: x["sort_time"])
    return sorted_m[:MAX_PER_LEAGUE]

def try_sofascore_enrich(rows):
    print("开始尝试从 Sofascore 获取长期 xG 数据...")
    cache = {}

    for i, row in enumerate(rows):
        home = row.get("主队", "")
        away = row.get("客队", "")
        print(f"[{i+1}/{len(rows)}] {home} vs {away}")

        for col, team in [("主队xG", home), ("客队xG", away)]:
            if not team:
                continue
            if team in cache:
                row[col] = cache[team]
                continue

            try:
                # 搜索球队
                q = requests.utils.quote(team)
                search_url = f"https://api.sofascore.com/api/v1/search/all?q={q}"
                data = sofascore_get(search_url)

                team_id = None
                if data and "results" in data:
                    for item in data["results"]:
                        if item.get("type") == "team":
                            entity = item.get("entity", {})
                            name = entity.get("name", "")
                            if team.lower() in name.lower() or name.lower() in team.lower():
                                team_id = entity.get("id")
                                print(f"  找到球队: {name} (id={team_id})")
                                break

                if not team_id:
                    print(f"  未找到球队: {team}")
                    cache[team] = None
                    continue

                # 尝试获取统计（先测试接口是否通）
                # 注意：不同联赛的 season / unique-tournament ID 不同，这里先做通用尝试
                stats = sofascore_get(f"https://api.sofascore.com/api/v1/team/{team_id}/statistics/seasons")
                if stats:
                    print(f"  {team} 获取到 seasons 数据")
                    # 这里暂时不解析具体 xG，先确认能拿到数据
                    # 后续根据实际返回结构再提取
                    cache[team] = "有数据"
                    row[col] = "有数据"
                else:
                    print(f"  {team} 无 seasons 数据")
                    cache[team] = None

                time.sleep(1.2)

            except Exception as e:
                print(f"  {team} 异常: {e}")
                cache[team] = None

    print("Sofascore 处理结束")
    return rows

def main():
    print("=== 脚本开始运行 ===")
    ts = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    all_rows = []

    for name, lid in LEAGUES:
        print(f"抓取 {name}...")
        rows = fetch_pinnacle(name, lid)
        print(f"  → {len(rows)} 场")
        for m in rows:
            row = {
                "联赛": name,
                "时间": m["time"],
                "主队": m["home"],
                "客队": m["away"],
                "主胜": m["1X2"].get("home"),
                "平局": m["1X2"].get("draw"),
                "客胜": m["1X2"].get("away"),
                "亚盘": m["ah"][0] if m["ah"] else None,
                "亚盘主": m["ah"][1] if m["ah"] else None,
                "亚盘客": m["ah"][2] if m["ah"] else None,
                "大小": m["ou"][0] if m["ou"] else None,
                "大球": m["ou"][1] if m["ou"] else None,
                "小球": m["ou"][2] if m["ou"] else None,
                "主队xG": None,
                "客队xG": None,
                "伤停": "",
            }
            all_rows.append(row)
        time.sleep(0.5)

 # all_rows = try_sofascore_enrich(all_rows)

    if not all_rows:
        print("没有抓到数据")
        return

    wb = Workbook()
    ws = wb.active
    ws.title = "盘口"
    headers = ["联赛","时间","主队","客队","主胜","平局","客胜","亚盘","亚盘主","亚盘客","大小","大球","小球","主队xG","客队xG","伤停"]
    ws.append(headers)
    for r in all_rows:
        ws.append([r.get(h) for h in headers])

    fname = f"league_odds_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    wb.save(fname)
    send_file(fname, caption=f"各大联赛早盘 {ts}\n共 {len(all_rows)} 场")
    print("Excel 已发送:", fname)

if __name__ == "__main__":
    main()
