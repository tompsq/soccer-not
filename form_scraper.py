import os, time, io, requests
from datetime import datetime, timedelta
from collections import defaultdict
from openpyxl import Workbook

T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")

# football-data 代码 → 中文名（无欧冠欧联）
LEAGUE_CSV = [
    ("英超", "E0"),
    ("英冠", "E1"),
    ("西甲", "SP1"),
    ("意甲", "I1"),
    ("德甲", "D1"),
    ("法甲", "F1"),
    ("荷甲", "N1"),
    ("葡超", "P1"),
    ("苏超", "SC0"),
    ("比甲", "B1"),
]

# 赛季文件夹：2627=26/27，失败再试 2526
SEASONS = ["2627", "2526"]
N_LAST = 6

H = {"User-Agent": "Mozilla/5.0"}

def now_my():
    return datetime.utcnow() + timedelta(hours=8)

def send_file(path, caption=""):
    if not T or not C:
        print("跳过TG:", path)
        return
    try:
        with open(path, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{T}/sendDocument",
                data={"chat_id": C, "caption": (caption or "")[:1000]},
                files={"document": f},
                timeout=60,
            )
        time.sleep(1)
    except Exception as e:
        print("发送失败:", e)

def download_csv(season, code):
    url = f"https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
    try:
        r = requests.get(url, headers=H, timeout=30)
        if r.status_code == 200 and "Date" in r.text[:500]:
            return r.text
        print(f"  无数据 {season}/{code}: {r.status_code}")
    except Exception as e:
        print(f"  下载失败 {season}/{code}: {e}")
    return None

def parse_matches(text):
    """返回 [(date, home, away, hg, ag), ...] 按日期升序"""
    import csv
    rows = list(csv.DictReader(io.StringIO(text)))
    out = []
    for row in rows:
        ds = (row.get("Date") or "").strip()
        home = (row.get("HomeTeam") or "").strip()
        away = (row.get("AwayTeam") or "").strip()
        try:
            hg = int(row.get("FTHG"))
            ag = int(row.get("FTAG"))
        except Exception:
            continue
        if not ds or not home or not away:
            continue
        # 日期格式 13/08/26 或 13/08/2026
        dt = None
        for fmt in ("%d/%m/%y", "%d/%m/%Y"):
            try:
                dt = datetime.strptime(ds, fmt)
                break
            except Exception:
                pass
        if not dt:
            continue
        out.append((dt, home, away, hg, ag))
    out.sort(key=lambda x: x[0])
    return out

def form_from_matches(matches, n=N_LAST):
    """
    matches: 该队参与的已完赛列表，每项
      (date, is_home, gf, ga, pts)
    返回 dict
    """
    matches = sorted(matches, key=lambda x: x[0])[-n:]
    if not matches:
        return None
    pts = gf = ga = 0
    seq = []
    for _, is_home, g_f, g_a, p in matches:
        pts += p
        gf += g_f
        ga += g_a
        if p == 3:
            seq.append("W")
        elif p == 1:
            seq.append("D")
        else:
            seq.append("L")
    return {
        "场次": len(matches),
        "积分": pts,
        "进球": gf,
        "失球": ga,
        "净胜": gf - ga,
        "战绩": "".join(seq),
    }

def build_team_forms(matches):
    """全联赛赛果 → 每队 all / home / away 近 n 场"""
    by_team = defaultdict(list)  # team -> [(date, is_home, gf, ga, pts)]
    for dt, home, away, hg, ag in matches:
        # 主队
        if hg > ag:
            hp, ap = 3, 0
        elif hg == ag:
            hp, ap = 1, 1
        else:
            hp, ap = 0, 3
        by_team[home].append((dt, True, hg, ag, hp))
        by_team[away].append((dt, False, ag, hg, ap))

    result = {}
    for team, lst in by_team.items():
        all_f = form_from_matches(lst, N_LAST)
        home_f = form_from_matches([x for x in lst if x[1]], N_LAST)
        away_f = form_from_matches([x for x in lst if not x[1]], N_LAST)
        result[team] = {"all": all_f, "home": home_f, "away": away_f}
    return result

def fetch_league_forms(cn_name, code):
    text = None
    used = None
    for season in SEASONS:
        text = download_csv(season, code)
        if text:
            used = season
            break
    if not text:
        return [], used
    matches = parse_matches(text)
    # 只用已结束（日期 < 今天）
    today = now_my().replace(hour=0, minute=0, second=0, microsecond=0)
    matches = [m for m in matches if m[0] < today]
    forms = build_team_forms(matches)
    rows = []
    for team in sorted(forms.keys()):
        a, h, aw = forms[team]["all"], forms[team]["home"], forms[team]["away"]
        rows.append({
            "联赛": cn_name,
            "球队": team,
            "近6场次": a["场次"] if a else 0,
            "近6积分": a["积分"] if a else None,
            "近6进球": a["进球"] if a else None,
            "近6失球": a["失球"] if a else None,
            "近6净胜": a["净胜"] if a else None,
            "近6战绩": a["战绩"] if a else "",
            "主场近6积分": h["积分"] if h else None,
            "主场近6进球": h["进球"] if h else None,
            "主场近6失球": h["失球"] if h else None,
            "主场近6战绩": h["战绩"] if h else "",
            "客场近6积分": aw["积分"] if aw else None,
            "客场近6进球": aw["进球"] if aw else None,
            "客场近6失球": aw["失球"] if aw else None,
            "客场近6战绩": aw["战绩"] if aw else "",
        })
    return rows, used

def main():
    ts = now_my().strftime("%Y-%m-%d %H:%M:%S")
    all_rows = []
    for cn, code in LEAGUE_CSV:
        print(f"抓取 {cn} ({code})...")
        rows, season = fetch_league_forms(cn, code)
        print(f"  → {len(rows)} 队 | 赛季文件夹 {season}")
        all_rows.extend(rows)
        time.sleep(0.8)

    wb = Workbook()
    ws = wb.active
    ws.title = "近6场状态"
    headers = [
        "联赛", "球队", "近6场次", "近6积分", "近6进球", "近6失球", "近6净胜", "近6战绩",
        "主场近6积分", "主场近6进球", "主场近6失球", "主场近6战绩",
        "客场近6积分", "客场近6进球", "客场近6失球", "客场近6战绩",
    ]
    ws.append([f"近{N_LAST}场状态 | {ts} | 数据源 football-data.co.uk"])
    ws.append([])
    ws.append(headers)
    for r in all_rows:
        ws.append([r.get(h) for h in headers])

    fname = f"form_last{N_LAST}_{now_my().strftime('%Y%m%d_%H%M')}.xlsx"
    wb.save(fname)
    send_file(fname, caption=f"近{N_LAST}场状态 {ts}\n共 {len(all_rows)} 队")
    print("已发送:", fname)

if __name__ == "__main__":
    main()
