import requests
from datetime import datetime

H = {"User-Agent":"Mozilla/5.0","Accept":"application/json","Origin":"https://www.pinnacle.com","Referer":"https://www.pinnacle.com/"}

def main():
    r = requests.get("https://guest.api.arcadia.pinnacle.com/0.1/sports/29/leagues", headers=H, timeout=20)
    if r.status_code != 200:
        print("HTTP", r.status_code, r.text[:200])
        return
    leagues = r.json()
    print(f"共 {len(leagues)} 个联赛")
    print("=" * 60)
    for l in leagues:
        lid = l.get("id")
        name = l.get("name", "")
        # 只打印可能的国际/国家队/友谊赛/预选赛
        if any(k in name.lower() for k in ["world", "euro", "qualif", "friend", "international", "nations", "cup"]):
            print(f"ID={lid}  |  {name}")
    print("=" * 60)
    print("=== 所有联赛（备用）===")
    for l in leagues:
        print(f"ID={l.get('id')}  |  {l.get('name','')}")

if __name__ == "__main__":
    main()
