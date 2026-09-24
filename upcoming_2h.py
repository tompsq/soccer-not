import requests
from datetime import datetime, timedelta

H = {"User-Agent":"Mozilla/5.0","Accept":"application/json","Origin":"https://www.pinnacle.com","Referer":"https://www.pinnacle.com/"}
LEAGUES = [("欧国联A",200719),("欧国联B",200721),("欧国联C",200726),("欧国联D",200727)]

def main():
    print("当前本地时间（GitHub Actions 是 UTC）:", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)
    for name, lid in LEAGUES:
        print(f"\n=== {name} (ID={lid}) ===")
        try:
            r = requests.get(f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{lid}/matchups", headers=H, timeout=20)
            if r.status_code != 200:
                print("  HTTP", r.status_code)
                continue
            data = r.json()
            print(f"  共 {len(data)} 条记录")
            count = 0
            for m in data:
                if m.get("type") != "matchup": continue
                ps = m.get("participants", [])
                if len(ps) < 2: continue
                home = next((p["name"] for p in ps if p.get("alignment") == "home"), "?")
                away = next((p["name"] for p in ps if p.get("alignment") == "away"), "?")
                start_raw = m.get("startTime", "")
                try:
                    # 原样解析，不做 +8 修正，直接看原始 UTC 时间
                    dt_utc = datetime.strptime(start_raw[:19], "%Y-%m-%dT%H:%M:%S")
                    dt_my = dt_utc + timedelta(hours=8)
                    print(f"  {home} vs {away}")
                    print(f"    原始UTC: {start_raw}")
                    print(f"    UTC+0 : {dt_utc.strftime('%Y-%m-%d %H:%M')}")
                    print(f"    UTC+8 : {dt_my.strftime('%Y-%m-%d %H:%M')} (马来西亚时间)")
                except Exception as e:
                    print(f"  {home} vs {away}  startTime={start_raw}  解析失败: {e}")
                count += 1
            if count == 0:
                print("  （无比赛数据）")
        except Exception as e:
            print("  异常:", e)

if __name__ == "__main__":
    main()
