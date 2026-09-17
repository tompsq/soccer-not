import os, requests

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
def get_odds():
    res = ["【赛前赔率、亚盘与大小球】"]
    for name, key in L.items():
        url = f"https://api.the-odds-api.com/v4/sports/{key}/odds/?apiKey={K}&regions=eu,us,uk&markets=h2h,spreads,totals"
        r = requests.get(url)
        if r.status_code != 200: continue
        data = r.json()
        if not isinstance(data, list): continue
        blk = []
        for m in data:
            raw_h, raw_a = m.get("home_team", ""), m.get("away_team", "")
            h, a = sn(raw_h), sn(raw_a)
            bm = m.get("bookmakers", [])
            h2h_str, sp_str, tot_str = "", "", ""
            all_spreads, all_totals = [], []
            for b in bm:
                for x in b.get("markets", []):
                    ots = x.get("outcomes", [])
                    if not h2h_str and x.get("key") == "h2h":
                        hp = next((o.get("price") for o in ots if o.get("name") == raw_h), None)
                        ap = next((o.get("price") for o in ots if o.get("name") == raw_a), None)
                        dp = next((o.get("price") for o in ots if o.get("name","").lower() == "draw"), None)
                        if hp and dp and ap: h2h_str = f"欧: {hp} {dp} {ap}"
                    elif x.get("key") == "spreads" and len(ots) == 2:
                        h_opt = next((o for o in ots if o.get("name") == raw_h), None)
                        a_opt = next((o for o in ots if o.get("name") == raw_a), None)
                        if h_opt and a_opt:
                            hp, ap = h_opt.get("price", 0), a_opt.get("price", 0)
                            all_spreads.append((abs(hp - ap), h_opt.get("point", 0), hp, ap))
                    elif x.get("key") == "totals" and len(ots) == 2:
                        o_opt = next((o for o in ots if o.get("name") == "Over"), None)
                        u_opt = next((o for o in ots if o.get("name") == "Under"), None)
                        if o_opt and u_opt:
                            op, up = o_opt.get("price", 0), u_opt.get("price", 0)
                            all_totals.append((abs(op - up), o_opt.get("point", 0), op, up))
            if all_spreads:
                all_spreads.sort(key=lambda x: x[0])
                b_sp = all_spreads[0]
                sp_str = f"亚: 主{b_sp[1]:+g} ({b_sp[2]}) / 客 ({b_sp[3]})"
            if all_totals:
                all_totals.sort(key=lambda x: x[0])
                b_tot = all_totals[0]
                tot_str = f"球: {b_tot[1]} (大{b_tot[2]} / 小{b_tot[3]})"
            if h:
                ml = [f"{h} vs {a}"]
                if h2h_str: ml.append(h2h_str)
                if sp_str: ml.append(sp_str)
                if tot_str: ml.append(tot_str)
                blk.append("\n".join(ml))
        if blk:
            res.append(f"\n[{name}]")
            res.extend(blk[:8])
    return "\n".join(res)

def get_scores():
    res = ["【近期完场比分】"]
    for name, key in L.items():
        url = f"https://api.the-odds-api.com/v4/sports/{key}/scores/?apiKey={K}&daysFrom=3"
        r = requests.get(url)
        if r.status_code != 200: continue
        data = r.json()
        if not isinstance(data, list): continue
        sc_list = []
        for m in data:
            raw_h, raw_a = m.get("home_team",""), m.get("away_team","")
            h, a = sn(raw_h), sn(raw_a)
            scs = m.get("scores")
            if scs:
                hs, as_ = "0", "0"
                for s in scs:
                    if s.get("name","") == raw_h: hs = s.get("score","0")
                    elif s.get("name","") == raw_a: as_ = s.get("score","0")
                sc_list.append(f"{h} {hs}-{as_} {a}")
        if sc_list:
            res.append(f"\n[{name}]")
            res.extend(sc_list[:8])
    return "\n".join(res)

if __name__ == "__main__":
    oc = get_odds()
    sc = get_scores()
    parts = []
    if oc != "【赛前赔率、亚盘与大小球】": parts.append(oc)
    if sc != "【近期完场比分】": parts.append(sc)
    final = "\n\n--------------------\n\n".join(parts)
    send(final)
    print("推送完成")
