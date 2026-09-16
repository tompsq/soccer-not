import os, requests
from datetime import datetime, timezone, timedelta

K = os.environ.get("ODDS_API_KEY")
T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")

L = {
    "英超":"soccer_epl", "西甲":"soccer_spain_la_liga", 
    "意甲":"soccer_italy_serie_a", "德甲":"soccer_germany_bundesliga",
    "欧冠":"soccer_uefa_champs_league"
}

M = {
    "Manchester City":"曼城", "Manchester United":"曼联", "Arsenal":"阿森纳",
    "Liverpool":"利物浦", "Chelsea":"切尔西", "Tottenham Hotspur":"热刺",
    "Real Madrid":"皇马", "Barcelona":"巴萨", "Bayern Munich":"拜仁"
}

def sn(n):
    return M.get(n, n)

def send(msg):
    u = f"https://api.telegram.org/bot{T}/sendMessage"
    requests.post(u, json={"chat_id":C, "text":msg, "parse_mode":"Markdown"})

def get_data():
    res = ["近期赛事比分与赔率"]
    for name, key in L.items():
        url = f"https://api.the-odds-api.com/v4/sports/{key}/odds/?apiKey={K}&regions=eu&markets=h2h"
        r = requests.get(url)
        if r.status_code != 200: continue
        data = r.json()
        if not isinstance(data, list): continue
        
        blk = []
        for m in data[:5]:
            h, a = sn(m.get("home_team","")), sn(m.get("away_team",""))
            bm = m.get("bookmakers", [])
            h2h = ""
            if bm:
                mk = bm[0].get("markets", [])
                for x in mk:
                    ots = x.get("outcomes", [])
                    if x.get("key") == "h2h" and len(ots) == 3:
                        h2h = f"{ots[0].get('price')} {ots[1].get('price')} {ots[2].get('price')}"
            if h and a and h2h:
                blk.append(f"{h} vs {a}\n{h2h}")
        if blk:
            res.append(f"\n【{name}】")
            res.extend(blk)
    return "\n".join(res)

if __name__ == "__main__":
    content = get_data()
    send(content)
    print("推送完成")
