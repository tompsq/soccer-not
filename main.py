import os, requests, datetime

K = os.environ.get("API_FOOTBALL_KEY")
T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")

HEADERS = {
    "x-apisports-key": K,
    "x-rapidapi-key": K
}

# 当前年份/赛季
CURRENT_SEASON = 2026

# 精简核心联赛列表，确保稳定出数据
L = {
    "英超": 39, "西甲": 140, "意甲": 135,
    "德甲": 78, "法甲": 61, "欧冠": 2
}

def send(msg):
    if not msg or not msg.strip():
        msg = "【赛事推送】当前未抓取到符合条件的赛事数据。"
    u = f"https://api.telegram.org/bot{T}/sendMessage"
    
    if len(msg) > 3800:
        lines, chunks, cur = msg.split("\n"), [], ""
        for l in lines:
            if len(cur) + len(l) + 1 > 3800:
                chunks.append(cur)
                cur = l
            else:
                cur = (cur + "\n" + l) if cur else l
        if cur: chunks.append(cur)
        for ch in chunks:
            requests.post(u, json={"chat_id": C, "text": ch})
    else:
        requests.post(u, json={"chat_id": C, "text": msg})

def get_scores():
    res = ["【近期完场比分】"]
    for name, lid in L.items():
        # 加上 season=2026 参数
        url = f"https://v3.football.api-sports.io/fixtures?league={lid}&season={CURRENT_SEASON}&last=5"
        r = requests.get(url, headers=HEADERS)
        if r.status_code != 200:
            print(f"[{name}] Fixtures 请求失败, 状态码: {r.status_code}")
            continue
            
        data = r.json().get("response", [])
        sc_list = []
        for item in data:
            status = item.get("fixture", {}).get("status", {}).get("short", "")
            if status in ["FT", "AET", "PEN"]:
                h = item["teams"]["home"]["name"]
                a = item["teams"]["away"]["name"]
                gh = item["goals"]["home"]
                ga = item["goals"]["away"]
                sc_list.append(f"{h} {gh}-{ga} {a}")
        if sc_list:
            res.append(f"\n[{name}]")
            res.extend(sc_list)
            
    return "\n".join(res)

def get_odds():
    res = ["【赛前赔率与盘口】"]
    for name, lid in L.items():
        # 获取接下来的 5 场比赛（加上 season=2026）
        url = f"https://v3.football.api-sports.io/fixtures?league={lid}&season={CURRENT_SEASON}&next=5"
        r = requests.get(url, headers=HEADERS)
        if r.status_code != 200:
            continue
            
        fixtures = r.json().get("response", [])
        blk = []
        for match in fixtures[:3]:  # 取前 3 场，避免请求次数过多
            fid = match["fixture"]["id"]
            h = match["teams"]["home"]["name"]
            a = match["teams"]["away"]["name"]
            
            # 请求具体比赛赔率
            odds_url = f"https://v3.football.api-sports.io/odds?fixture={fid}"
            or_res = requests.get(odds_url, headers=HEADERS)
            if or_res.status_code != 200:
                continue
                
            odata = or_res.json().get("response", [])
            h2h_str, sp_str, tot_str = "", "", ""
            
            if odata and odata[0].get("bookmakers"):
                bm = odata[0]["bookmakers"][0]
                for bet in bm.get("bets", []):
                    bet_id = bet.get("id")
                    values = bet.get("values", [])
                    if bet_id == 1 and not h2h_str:
                        hp = next((v["odd"] for v in values if v["value"] == "Home"), None)
                        dp = next((v["odd"] for v in values if v["value"] == "Draw"), None)
                        ap = next((v["odd"] for v in values if v["value"] == "Away"), None)
                        if hp and dp and ap: h2h_str = f"欧: {hp} {dp} {ap}"
                    elif bet_id == 8 and not sp_str:
                        h_opt = next((v for v in values if "Home" in str(v["value"])), None)
                        a_opt = next((v for v in values if "Away" in str(v["value"])), None)
                        if h_opt and a_opt:
                            sp_str = f"亚: 主{h_opt.get('value')} ({h_opt.get('odd')}) / 客 ({a_opt.get('odd')})"
                    elif bet_id == 5 and not tot_str:
                        o_opt = next((v for v in values if "Over" in str(v["value"])), None)
                        u_opt = next((v for v in values if "Under" in str(v["value"])), None)
                        if o_opt and u_opt:
                            tot_str = f"球: {o_opt.get('value')} (大{o_opt.get('odd')} / 小{u_opt.get('odd')})"
            
            ml = [f"{h} vs {a}"]
            if h2h_str: ml.append(h2h_str)
            if sp_str: ml.append(sp_str)
            if tot_str: ml.append(tot_str)
            blk.append("\n".join(ml))
            
        if blk:
            res.append(f"\n[{name}]")
            res.extend(blk)
            
    return "\n".join(res)

if __name__ == "__main__":
    sc = get_scores()
    oc = get_odds()
    parts = []
    if len(sc.split("\n")) > 1: parts.append(sc)
    if len(oc.split("\n")) > 1: parts.append(oc)
    
    final = "\n\n--------------------\n\n".join(parts) if parts else "【赛事推送】当前未抓取到符合条件的赛事数据。"
    send(final)
    print("运行完成")
