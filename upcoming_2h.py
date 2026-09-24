import os, time, requests
from datetime import datetime, timedelta

T, C = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")
WINDOW_HOURS = 5
LEAGUES = [("英超",1980),("英冠",1977),("西甲",2196),("德甲",1842),("意甲",2436),("法甲",2036),("葡超",2386),("苏超",2421),("希超",2081),("欧冠",2627),("欧联",2630),("欧洲国家入选赛",2666)]
H = {"User-Agent":"Mozilla/5.0","Accept":"application/json","Origin":"https://www.pinnacle.com","Referer":"https://www.pinnacle.com/"}

def send(t):
    if not T or not C: print(t); return
    try: requests.post(f"https://api.telegram.org/bot{T}/sendMessage",json={"chat_id":C,"text":t[:4000],"parse_mode":"Markdown"},timeout=30); time.sleep(1.2)
    except Exception as e: print(e)

def to_dec(a):
    try:
        a=float(a)
        return round(a/100+1,3) if a>0 else round(100/abs(a)+1,3)
    except: return None

def get(url):
    for _ in range(3):
        try:
            r=requests.get(url,headers=H,timeout=20)
            if r.status_code==200: return r.json()
        except: time.sleep(1.5)
    return None

def fetch(name, lid, t_start, t_end):
    ms = get(f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{lid}/matchups")
    if not ms: return []
    matches={}
    for m in ms:
        if m.get("type")!="matchup": continue
        st=m.get("startTime","")
        if not st: continue
        try: mt=datetime.strptime(st[:19],"%Y-%m-%dT%H:%M:%S")+timedelta(hours=8)
        except: continue
        if not (t_start<=mt<=t_end): continue
        ps=m.get("participants",[])
        if len(ps)<2: continue
        home=next((p["name"] for p in ps if p.get("alignment")=="home"),None)
        away=next((p["name"] for p in ps if p.get("alignment")=="away"),None)
        if not home or not away: continue
        matches[m["id"]]={"home":home,"away":away,"time":mt.strftime("%m-%d %H:%M"),"1X2":{},"ah":None,"ou":None}
    if not matches: return []
    mks=get(f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{lid}/markets/straight")
    if not mks: return []
    for mk in mks:
        mid=mk.get("matchupId")
        if mid not in matches or mk.get("period")!=0 or mk.get("isAlternate") is True: continue
        t,ps=mk.get("type"),mk.get("prices",[])
        if t=="moneyline":
            for p in ps:
                d=p.get("designation")
                if d in ("home","draw","away"): matches[mid]["1X2"][d]=to_dec(p["price"])
        elif t=="spread":
            hp=next((p for p in ps if p.get("designation")=="home"),None)
            ap=next((p for p in ps if p.get("designation")=="away"),None)
            if hp and ap:
                line=hp.get("points",0)
                if matches[mid]["ah"] is None or abs(line)<abs(matches[mid]["ah"][0]):
                    matches[mid]["ah"]=(line,to_dec(hp["price"]),to_dec(ap["price"]))
        elif t=="total":
            op=next((p for p in ps if p.get("designation")=="over"),None)
            up=next((p for p in ps if p.get("designation")=="under"),None)
            if op and up:
                line=op.get("points",0)
                if matches[mid]["ou"] is None or abs(line-2.5)<abs(matches[mid]["ou"][0]-2.5):
                    matches[mid]["ou"]=(line,to_dec(op["price"]),to_dec(up["price"]))
    return sorted(matches.values(), key=lambda x: x["time"])

def main():
    now=datetime.now()
    t_start, t_end = now, now+timedelta(hours=WINDOW_HOURS)
    ts=now.strftime("%Y-%m-%d %H:%M:%S")
    print(f"抓取窗口：{t_start.strftime('%m-%d %H:%M')} ~ {t_end.strftime('%m-%d %H:%M')}，共 {len(LEAGUES)} 个联赛")
    all_msg=[]
    for name,lid in LEAGUES:
        print(f"抓取 {name} ...")
        rows=fetch(name,lid,t_start,t_end)
        if not rows: continue
        lines=[f"🏆 *【{name}】* （{len(rows)} 场）"]
        for m in rows:
            s=f"⚽ *{m['home']} vs {m['away']}* 🕒 `{m['time']}`"
            if len(m["1X2"])>=3: s+=f"\n   🔹 `1X2` : {m['1X2']['home']} | {m['1X2']['draw']} | {m['1X2']['away']}"
            if m["ah"]:
                line,ho,ao=m["ah"]
                ls=f"{line:+g}" if line!=0 else "0"
                s+=f"\n   🔹 `亚盘` : 主{ls} {ho} | 客 {ao}"
            if m["ou"]:
                line,oo,uo=m["ou"]
                s+=f"\n   🔹 `大小` : {line} 大{oo} | 小{uo}"
            lines.append(s)
        all_msg.append("\n\n".join(lines))
        time.sleep(0.8)
    if not all_msg:
        send(f"⚠️ `{ts}` 未来 {WINDOW_HOURS} 小时内没有比赛。")
        return
    chunks, cur = [], ""
    for block in all_msg:
        if len(cur)+len(block)+4>3800: chunks.append(cur); cur=block
        else: cur += ("\n\n" if cur else "")+block
    if cur: chunks.append(cur)
    total=len(chunks)
    for idx,ch in enumerate(chunks,1):
        title = f"⏰ *【未来 {WINDOW_HOURS} 小时内赛事"
        if total>1: title += f" ({idx}/{total})"
        title += f"】*\n🕒 `{ts}`\n\n"
        send(title+ch)

if __name__ == "__main__":
    main()
