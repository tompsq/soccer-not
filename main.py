import os, requests
from datetime import datetime, timezone, timedelta

K = os.environ.get("ODDS_API_KEY")
T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")

L = {
    "英超":"soccer_epl", "英冠":"soccer_efl_champ",
    "西甲":"soccer_spain_la_liga", "意甲":"soccer_italy_serie_a",
    "德甲":"soccer_germany_bundesliga", "欧冠":"soccer_uefa_champs_league",
    "欧联":"soccer_uefa_europa_league", "葡超":"soccer_portugal_primeira_liga",
    "荷甲":"soccer_netherlands_eredivisie", "苏超":"soccer_spl",
    "希超":"soccer_greece_super_league"
}

M = {
    "Manchester City":"曼城", "Manchester United":"曼联", "Arsenal":"阿森纳",
    "Liverpool":"利物浦", "Chelsea":"切尔西", "Tottenham Hotspur":"热刺",
    "Aston Villa":"维拉", "Newcastle United":"纽卡", "Brighton":"布莱顿",
    "Real Madrid":"皇马", "Barcelona":"巴萨", "Atletico Madrid":"马竞",
    "Bayern Munich":"拜仁", "Borussia Dortmund":"多特", "Bayer Leverkusen":"勒沃库森",
    "Inter Milan":"国米", "AC Milan":"AC米兰", "Juventus":"尤文", "Napoli":"那不勒斯",
    "Paris Saint-Germain":"巴黎", "Marseille":"马赛"
}

def sn(n):
    return M.get(n, n)

def send(msg):
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
            requests.post(u, json={"chat_id":C, "text":ch, "parse_mode":"Markdown"})
    else:
        requests.post(u, json={"chat_id":C, "text":msg, "parse_mode":"Markdown"})

def get_odds():
    res = ["【赛前赔率、亚盘与大小球】"]
    for name, key in L.items():
        url = f"https://api.the-odds-api.com/v4/sports/{key}/odds/?apiKey={K}&regions=eu&markets=h2h,spreads,totals"
        r = requests.get(url)
        if r.status_code != 200: continue
        data = r.json()
        if not isinstance(data, list): continue
        blk = []
        for m in data[:10]:
            h, a = sn(m.get("home_team","")), sn(m.get("away_team",""))
            bm = m.get("bookmakers", [])
            h2h_str, sp_str, tot_str = "", "", ""
            all_spreads, all_totals = [], []

            for b in bm:
                mk = b.get("markets", [])
                for x in mk:
                    ots = x.get("outcomes", [])
                    if not h2h_str and x.get("key") == "h2h" and len(ots) == 3:
                        h2h_str = f"欧: {ots[0].get('price')} {ots[1].get('price')} {ots[2].get('price')}"
                    elif x.get("key") == "spreads" and len(ots) == 2:
                        p0, p1 = ots[0].get("price", 0), ots[1].get("price", 0)
                        all_spreads.append((abs(p0 - p1), ots[0].get("point"), p0, p1))
                    elif x.get("key") == "totals" and len(ots) == 2:
                        p0, p1 = ots[0].get("price", 0), ots[1].get("price", 0)
                        all_totals.append((abs(p0 - p1), ots[0].get("point"), p0, p1))
            
            if all_spreads:
                all_spreads.sort(key=lambda x: x[0])
                b_sp = all_spreads[0]
                sp_str = f"亚: 主{b_sp[1]:+g} ({b_sp[2]}) / 客 ({b_sp[3]})"
                
            if all_totals:
                all_totals.sort(key=lambda x: x[0])
                b_tot = all_totals[0]
                tot_str = f"球: {b_tot[1]} (大{b_tot[2]} / 小{b_tot[3]})"

            if h and (h2h_str or sp_str or tot_str):
                ml = [f"{h} vs {a}"]
                if h2h_str: ml.append(h2h_str)
                if sp_str: ml.append(sp_str)
                if tot_str: ml.append(tot_str)
                blk.append("\n".join(ml))
        if blk:
            res.append(f"\n[{name}]")
            res.extend(blk)
    return "\n".join(res)
def get_scores():
    res = ["【近期完场比分】"]
    for name, key in L.items():
        url = f"https://api.the-odds-api.com/v4/sports/{key}/scores/?apiKey={K}&daysFrom=3"
        r = requests.get(url)
        if r.status_code != 200: continue
        data = r.json()
        if not isinstance(data, list): continue
        comp = [m for m in data if m.get("completed") == True]
        if not comp: continue
        sc_list = []
        for m in comp[:10]:
            h, a = sn(m.get("home_team","")), sn(m.get("away_team",""))
            scs = m.get("scores", [])
            hs, as_ = "0", "0"
            for s in scs:
                if sn(s.get("name","")) == h:
                    hs = s.get("score","0")
                elif sn(s.get("name","")) == a:
                    as_ = s.get("score","0")
            sc_list.append(f"{h} {hs}-{as_} {a}")
        if sc_list:
            res.append(f"\n[{name}]")
            res.extend(sc_list)
    return "\n".join(res)

if __name__ == "__main__":
    oc = get_odds()
    sc = get_scores()
    parts = []
    if sc != "【近期完场比分】": parts.append(sc)
    if oc != "【赛前赔率、亚盘与大小球】": parts.append(oc)
    final = "\n\n--------------------\n\n".join(parts)
    send(final)
    print("推送完成")
