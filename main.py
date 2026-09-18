import os, requests

K = os.environ.get("API_FOOTBALL_KEY")
T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")

# 双重验证头，彻底解决 Missing application key 报错[span_0](start_span)[span_0](end_span)
HEADERS = {
    "x-apisports-key": K,
    "x-rapidapi-key": K
}

# 11 个主流联赛及 API-Football ID
L = {
    "英超": 39, "英冠": 40, "西甲": 140, "意甲": 135,
    "德甲": 78, "欧冠": 2, "欧联": 3, "葡超": 94,
    "荷甲": 88, "苏超": 179, "希超": 197
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
            res = requests.post(u, json={"chat_id": C, "text": ch})
            print(f"TG响应状态: {res.status_code}")
    else:
        res = requests.post(u, json={"chat_id": C, "text": msg})
        print(f"TG响应状态: {res.status_code}")

def get_scores():
    res = ["【近期完场比分】"]
    for name, lid in L.items():
        url = f"https://v3.football.api-sports.io/fixtures?league={lid}&last=10&status=FT"
        r = requests.get(url, headers=HEADERS)
        if r.status_code != 200: continue
        data = r.json().get("response", [])
        if not data: continue
        
        sc_list = []
        for item in data[:8]:
            h = item["teams"]["home"]["name"]
            a = item["teams"]["away"]["name"]
            gh = item["goals"]["home"]
            ga = item["goals"]["away"]
            if gh is not None and ga is not None:
                sc_list.append(f"{h} {gh}-{ga} {a}")
        if sc_list:
            res.append(f"\n[{name}]")
            res.extend(sc_list)
    return "\n".join(res)
def get_odds():
    res = ["【赛前赔率、亚盘与大小球】"]
    for name, lid in L.items():
        url = f"https://v3.football.api-sports.io/odds?league={lid}&season=2026"
        r = requests.get(url, headers=HEADERS)
        if r.status_code != 200: continue
        data = r.json().get("response", [])
        if not data: continue
        
        blk = []
        for match in data[:8]:
            h = match["teams"]["home"]["name"]
            a = match["teams"]["away"]["name"]
            bookmakers = match.get("bookmakers", [])
            if not bookmakers: continue
            
            bm = bookmakers[0]
            h2h_str, sp_str, tot_str = "", "", ""
            
            for bet in bm.get("bets", []):
                bet_id = bet.get("id")
                values = bet.get("values", [])
                
                # 欧赔 (Match Winner)
                if bet_id == 1 and not h2h_str:
                    hp = next((v["odd"] for v in values if v["value"] == "Home"), None)
                    dp = next((v["odd"] for v in values if v["value"] == "Draw"), None)
                    ap = next((v["odd"] for v in values if v["value"] == "Away"), None)
                    if hp and dp and ap:
                        h2h_str = f"欧: {hp} {dp} {ap}"
                
                # 亚盘 (Asian Handicap)
                elif bet_id == 8 and not sp_str:
                    h_opt = next((v for v in values if "Home" in str(v["value"])), None)
                    a_opt = next((v for v in values if "Away" in str(v["value"])), None)
                    if h_opt and a_opt:
                        sp_str = f"亚: 主{h_opt.get('value')} ({h_opt.get('odd')}) / 客 ({a_opt.get('odd')})"
                
                # 大小球 (Goals Over/Under)
                elif bet_id == 5 and not tot_str:
                    o_opt = next((v for v in values if "Over" in str(v["value"])), None)
                    u_opt = next((v for v in values if "Under" in str(v["value"])), None)
                    if o_opt and u_opt:
                        tot_str = f"球: {o_opt.get('value')} (大{o_opt.get('odd')} / 小{u_opt.get('odd')})"
            
            if h2h_str or sp_str or tot_str:
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
    if sc != "【近期完场比分】": parts.append(sc)
    if oc != "【赛前赔率、亚盘与大小球】": parts.append(oc)
    
    final = "\n\n--------------------\n\n".join(parts)
    send(final)
    print("运行完成")
