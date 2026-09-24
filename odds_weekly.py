import os, time, requests
from datetime import datetime

T, C = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")
LEAGUES = [("英超",1980,10),("英冠",1977,None),("西甲",2196,10),("德甲",1842,10),("意甲",2436,10),("法甲",2036,10),("葡超",2386,10),("苏超",2421,10),("希超",2081,10),("欧冠",2627,10),("欧联",2630,10)]
H = {"User-Agent":"Mozilla/5.0","Accept":"application/json","Origin":"https://www.pinnacle.com","Referer":"https://www.pinnacle.com/"}

def send(t):
    if not T or not C: print(t); return
    try: requests.post(f"https://api.telegram.org/bot{T}/sendMessage",json={"chat_id":C,"text":t[:4000],"parse_mode":"Markdown"},timeout=30); time.sleep(1.2)
    except Exception as e: print(e)

def to_dec(a):
    try:
        a=float(a)
        return round(a/100+1,3) if a>0 else round(100/abs(a)+1,3)
    except: return 0.0

def get(url):
    for _ in range(3):
        try:
            r=requests.get(url,headers=H,timeout=20)
            if r.status_code==200: return r.json()
        except: time.sleep(1.5)
    return None

def fetch(name, lid, maxn=10):
    ms = get(f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{lid}/matchups")
    if not ms: return []
    matches={}
    for m in ms:
        if m.get("type")!="matchup": continue
        ps=m.get("participants",[])
        if len(ps)<2: continue
        home=next((p["name"] for p in ps if p.get("alignment")=="home"),None)
        away=next((p["name"] for p in ps if p.get("alignment")=="away"),None)
        if not home or not away: continue
        matches[m["id"]]={"home":home,"away":away,"time":m.get("startTime","")[:16].replace("T"," "),"1X2":{},"ah":None,"ou":None}
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
    sorted_m=sorted(matches.values(),key=lambda x:x["time"] or "9999")
    if maxn is not None: sorted_m=sorted_m[:maxn]
    res=[]
    for m in sorted_m:
        ls=[f"⚽ *{m['home']} vs {m['away']}* 🕒 `{m['time']}`"]
        if len(m["1X2"])>=3:
            ls.append(f"   🔹 `1X2` : {m['1X2'].get('home','-')} | {m['1X2'].get('draw','-')} | {m['1X2'].get('away','-')}")
        if m["ah"]:
            line,ho,ao=m["ah"]
            line_str = f"{line:+g}" if line != 0 else "0"
            ls.append(f"   🔹 `亚盘` : 主{line_str} {ho} | 客 {ao}")
        if m["ou"]:
            line,oo,uo=m["ou"]
            ls.append(f"   🔹 `大小` : {line} 大{oo} | 小{uo}")
        if len(ls)>1: res.append("\n".join(ls))
    return res

def main():
    ts=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msgs=[]
    for name,lid,maxn in LEAGUES:
        print(f"抓取 {name}...")
        ms=fetch(name,lid,maxn)
        if ms: msgs.append(f"🏆 *【{name}】* （共{len(ms)}场）\n\n"+"\n\n".join(ms))
        time.sleep(0.8)
    if not msgs: send(f"⚠️ `{ts}` 无数据"); return
    cur=f"🎯 *Pinnacle 多联赛盘口*\n🕒 `{ts}`\n\n"
    for b in msgs:
        if len(cur)+len(b)>3800: send(cur.strip()); cur=b+"\n\n"
        else: cur+=b+"\n\n"
    if cur.strip(): send(cur.strip())

if __name__=="__main__": main()
