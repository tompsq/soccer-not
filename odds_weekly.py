import os, time, requests
from datetime import datetime
from openpyxl import Workbook

T, C = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")
LEAGUES = [("英超",1980,10),("英冠",1977,None),("西甲",2196,10),("德甲",1842,10),("意甲",2436,10),("法甲",2036,10),("葡超",2386,10),("苏超",2421,10),("希超",2081,10),("欧冠",2627,10),("欧联",2630,10)]
H = {"User-Agent":"Mozilla/5.0","Accept":"application/json","Origin":"https://www.pinnacle.com","Referer":"https://www.pinnacle.com/"}

def send(t):
    if not T or not C: print(t); return
    try: requests.post(f"https://api.telegram.org/bot{T}/sendMessage",json={"chat_id":C,"text":t[:4000],"parse_mode":"Markdown"},timeout=30); time.sleep(1.2)
    except Exception as e: print(e)

def send_file(path, caption=""):
    if not T or not C: print("文件已生成:", path); return
    try:
        with open(path, "rb") as f:
            requests.post(f"https://api.telegram.org/bot{T}/sendDocument", data={"chat_id":C,"caption":caption}, files={"document":f}, timeout=60)
        time.sleep(1.5)
    except Exception as e: print("发送文件失败:", e)

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
    rows=[]
    for m in sorted_m:
        row={"联赛":name,"主队":m["home"],"客队":m["away"],"时间":m["time"],
             "主胜":m["1X2"].get("home"),"平局":m["1X2"].get("draw"),"客胜":m["1X2"].get("away"),
             "亚盘":None,"亚盘主":None,"亚盘客":None,"大小":None,"大球":None,"小球":None}
        if m["ah"]:
            line,ho,ao=m["ah"]
            row["亚盘"]=line
            row["亚盘主"]=ho
            row["亚盘客"]=ao
        if m["ou"]:
            line,oo,uo=m["ou"]
            row["大小"]=line
            row["大球"]=oo
            row["小球"]=uo
        rows.append(row)
    return rows

def main():
    ts=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    all_rows=[]
    msgs=[]
    for name,lid,maxn in LEAGUES:
        print(f"抓取 {name}...")
        rows=fetch(name,lid,maxn)
        if rows:
            all_rows.extend(rows)
            summary=[]
            for r in rows:
                s=f"⚽ *{r['主队']} vs {r['客队']}* 🕒 `{r['时间']}`"
                if r["主胜"]: s+=f"\n   🔹 `1X2` : {r['主胜']} | {r['平局']} | {r['客胜']}"
                if r["亚盘"] is not None:
                    ls=f"{r['亚盘']:+g}" if r["亚盘"]!=0 else "0"
                    s+=f"\n   🔹 `亚盘` : 主{ls} {r['亚盘主']} | 客 {r['亚盘客']}"
                if r["大小"] is not None: s+=f"\n   🔹 `大小` : {r['大小']} 大{r['大球']} | 小{r['小球']}"
                summary.append(s)
            msgs.append(f"🏆 *【{name}】* （共{len(rows)}场）\n\n"+"\n\n".join(summary))
        time.sleep(0.8)

    if not all_rows:
        send(f"⚠️ `{ts}` 无数据")
        return

    # 用 openpy
    wb = Workbook()
    ws = wb.active
    ws.title = "盘口"
    headers = ["联赛","时间","主队","客队","主胜","平局","客胜","亚盘","亚盘主","亚盘客","大小","大球","小球"]
    ws.append(headers)
    for r in all_rows:
        ws.append([r.get(h) for h in headers])
    fname = f"pinnacle_odds_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    wb.save(fname)

    # 发文字
    cur=f"🎯 *Pinnacle 多联赛盘口*\n🕒 `{ts}`\n共 {len(all_rows)} 场\n\n"
    for b in msgs:
        if len(cur)+len(b)>3800: send(cur.strip()); cur=b+"\n\n"
        else: cur+=b+"\n\n"
    if cur.strip(): send(cur.strip())

    # 发 Excel
    send_file(fname, caption=f"Pinnacle 盘口数据 {ts}（共{len(all_rows)}场）")
    print("Excel 已生成并发送:", fname)

if __name__=="__main__": main()
