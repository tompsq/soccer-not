import os, io, csv, requests
from datetime import datetime, timedelta
from openpyxl import Workbook

T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")
FD_TOKEN = os.environ.get("FOOTBALL_DATA_TOKEN")

COUK = [
    ("E0", "英超"), ("SP1", "西甲"), ("I1", "意甲"), ("D1", "德甲"),
    ("F1", "法甲"), ("B1", "比甲"), ("N1", "荷甲"), ("T1", "土超"),
    ("G1", "希超"), ("E1", "英冠"),
]
ORG = [("CL", "欧冠"), ("EL", "欧足协")]

def send_file(path, caption=""):
    if not T or not C:
        print("文件:", path)
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

def parse_date(s):
    s = (s or "").strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    return None

def season_folders():
    y, m = datetime.utcnow().year, datetime.utcnow().month
    start = y if m >= 7 else y - 1
    a = f"{str(start)[2:]}{str(start+1)[2:]}"
    b = f"{str(start-1)[2:]}{str(start)[2:]}"
    return [a, b]

def fetch_couk(code, name, d0, d1):
    rows = []
    for season in season_folders():
        url = f"https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
        try:
            r = requests.get(url, timeout=25)
            if r.status_code != 200 or "HomeTeam" not in r.text[:500]:
                print(f"  {name} {season}: HTTP {r.status_code}")
                continue
            reader = csv.DictReader(io.StringIO(r.text))
            n = 0
            for row in reader:
                dt = parse_date(row.get("Date") or "")
                if not dt or not (d0 <= dt <= d1):
                    continue
                home = row.get("HomeTeam") or ""
                away = row.get("AwayTeam") or ""
                hg = row.get("FTHG") or ""
                ag = row.get("FTAG") or ""
                if home and away and hg != "" and ag != "":
                    rows.append({
                        "联赛": name, "日期": dt.isoformat(),
                        "主队": home, "客队": away,
                        "比分": f"{hg}-{ag}", "主进球": hg, "客进球": ag,
                    })
                    n += 1
            print(f"  {name} {season}: 命中 {n} 场")
            if n or rows:
                break
        except Exception as e:
            print(f"  {name} 错误: {e}")
    return rows

def fetch_org(code, name, d0, d1):
    if not FD_TOKEN:
        print(f"  {name}: 无 FOOTBALL_DATA_TOKEN，跳过")
        return []
    try:
        r = requests.get(
            f"https://api.football-data.org/v4/competitions/{code}/matches",
            headers={"X-Auth-Token": FD_TOKEN},
            params={"dateFrom": d0.isoformat(), "dateTo": d1.isoformat(), "status": "FINISHED"},
            timeout=25,
        )
        print(f"  {name}: HTTP {r.status_code}")
        if r.status_code != 200:
            print(r.text[:150])
            return []
        rows = []
        for m in (r.json().get("matches") or []):
            ft = ((m.get("score") or {}).get("fullTime") or {})
            hg, ag = ft.get("home"), ft.get("away")
            if hg is None or ag is None:
                continue
            rows.append({
                "联赛": name,
                "日期": (m.get("utcDate") or "")[:10],
                "主队": (m.get("homeTeam") or {}).get("name") or "",
                "客队": (m.get("awayTeam") or {}).get("name") or "",
                "比分": f"{hg}-{ag}",
                "主进球": hg,
                "客进球": ag,
            })
        print(f"  {name}: {len(rows)} 场")
        return rows
    except Exception as e:
        print(f"  {name} 错误: {e}")
        return []

def main():
    now = datetime.utcnow()
    d1, d0 = now.date(), now.date() - timedelta(days=3)
    print(f"窗口(UTC): {d0} \~ {d1}")

    all_rows = []
    for code, name in COUK:
        all_rows.extend(fetch_couk(code, name, d0, d1))
    for code, name in ORG:
        all_rows.extend(fetch_org(code, name, d0, d1))

    all_rows.sort(key=lambda x: (x["日期"], x["联赛"], x["主队"]))

    wb = Workbook()
    ws = wb.active
    ws.title = "近3天完场"
    ws.append(["联赛", "日期", "主队", "客队", "比分", "主进球", "客进球"])
    for r in all_rows:
        ws.append([r["联赛"], r["日期"], r["主队"], r["客队"], r["比分"], r["主进球"], r["客进球"]])

    by_l = {}
    for r in all_rows:
        by_l.setdefault(r["联赛"], []).append(r)
    for league, rows in by_l.items():
        w = wb.create_sheet(league[:28])
        w.append(["日期", "主队", "客队", "比分"])
        for r in rows:
            w.append([r["日期"], r["主队"], r["客队"], r["比分"]])

    fname = f"recent_results_{now.strftime('%Y%m%d_%H%M')}.xlsx"
    wb.save(fname)
    send_file(fname, caption=f"近3天完场比分\n{d0} \~ {d1} (UTC)\n共 {len(all_rows)} 场 / {len(by_l)} 联赛")
    print("已发送:", fname, "场次:", len(all_rows))

if __name__ == "__main__":
    main()
