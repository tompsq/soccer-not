import os, sys, json, requests
import pandas as pd
from datetime import datetime, timedelta, timezone

API_HOST = "v3.football.api-sports.io"

def main():
    API_KEY = os.environ.get("API_FOOTBALL_KEY", "")
    if not API_KEY: sys.exit(1)
    headers = {'x-rapidapi-host': API_HOST, 'x-rapidapi-key': API_KEY}
    
    SHA_TZ = timezone(timedelta(hours=8))
    TODAY_STR = datetime.now(SHA_TZ).strftime('%Y-%m-%d')
    url = f"https://{API_HOST}/fixtures?date={TODAY_STR}"
    
    try:
        all_fixtures = requests.get(url, headers=headers, timeout=20).json().get("response", [])
    except:
        sys.exit(1)

    LEAGUE_IDS =
    fixtures = [f for f in all_fixtures if f.get("league", {}).get("id") in LEAGUE_IDS]
    if not fixtures: fixtures = all_fixtures[:3]
    if not fixtures: sys.exit(1)
    
    sheet1, sheet2, sheet3, sheet4 = [], [], [], []

    for item in fixtures[:5]:
        fid = item.get("fixture", {}).get("id")
        lname = item.get("league", {}).get("name")
        mdate = item.get("fixture", {}).get("date", "")[:10]
        hid, aid = item['teams']['home']['id'], item['teams']['away']['id']
        hname, aname = item['teams']['home']['name'], item['teams']['away']['name']
        title = f"{hname} VS {aname}"
        
        h_win, d_win, a_win = "", "", ""
        try:
            o_res = requests.get(f"https://{API_HOST}/odds?fixture={fid}", headers=headers).json().get("response", [])
            if o_res:
                for bm in o_res[0].get("bookmakers", []):
                    if bm.get("name") in ["William Hill", "Bet365"]:
                        for bet in bm.get("bets", []):
                            if bet.get("name") == "Match Winner":
                                for val in bet.get("values", []):
                                    if val.get("value") == "Home": h_win = val.get("odd")
                                    elif val.get("value") == "Draw": d_win = val.get("odd")
                                    elif val.get("value") == "Away": a_win = val.get("odd")
                                break
        except: pass
            
        sheet1.append({"比赛ID": fid, "联赛": lname, "日期": mdate, "对阵": title, "初盘-主胜": h_win, "初盘-平局": d_win, "初盘-客胜": a_win})
        
        s_dict = {"对阵": title, "主队": hname, "客队": aname, "主队_场均进球": 0.0, "客队_场均进球": 0.0}
        try:
            h_res = requests.get(f"https://{API_HOST}/teams/statistics?season=2026&team={hid}&league={item['league']['id']}", headers=headers).json().get("response", {})
            s_dict["主队_场均进球"] = h_res.get("goals", {}).get("for", {}).get("average", {}).get("total", 0.0)
            a_res = requests.get(f"https://{API_HOST}/teams/statistics?season=2026&team={aid}&league={item['league']['id']}", headers=headers).json().get("response", {})
            s_dict["客队_场均进球"] = a_res.get("goals", {}).get("for", {}).get("average", {}).get("total", 0.0)
        except: pass
        sheet2.append(s_dict)
        
        try:
            h_res = requests.get(f"https://{API_HOST}/fixtures/headtohead?h2h={hid}-{aid}", headers=headers).json().get("response", [])
            for h_m in h_res[:5]:
                sheet3.append({
                    "当前对阵": title, "历史交战日期": h_m.get("fixture", {}).get("date", "")[:10],
                    "历史主队": h_m.get("teams", {}).get("home", {}).get("name"), "历史客队": h_m.get("teams", {}).get("away", {}).get("name"),
                    "具体比分赛果": f"{h_m.get('goals', {}).get('home')}:{h_m.get('goals', {}).get('away')}"
                })
        except: pass

        try:
            inj_res = requests.get(f"https://{API_HOST}/injuries?fixture={fid}", headers=headers).json().get("response", [])
            if not inj_res:
                sheet4.append({"对阵": title, "球队": "全员健康", "伤停人员": "无", "缺阵类型": "无", "缺阵原因": "无"})
            for inj in inj_res:
                sheet4.append({
                    "对阵": title, "球队": inj.get("team", {}).get("name"), "伤停人员": inj.get("player", {}).get("name"),
                    "缺阵类型": inj.get("player", {}).get("type", "伤病"), "缺阵原因": inj.get("player", {}).get("reason", "未知")
                })
        except: pass

    try:
        out_name = "Football_AI_Model_Data.xlsx"
        with pd.ExcelWriter(out_name, engine="openpyxl") as writer:
            pd.DataFrame(sheet1).to_excel(writer, sheet_name="1_五大联赛概要与赔率", index=False)
            pd.DataFrame(sheet2).to_excel(writer, sheet_name="2_大样本进阶场均统计", index=False)
            pd.DataFrame(sheet3).to_excel(writer, sheet_name="3_历史交锋H2H具体赛果", index=False)
            pd.DataFrame(sheet4).to_excel(writer, sheet_name="4_官方实战伤停名单明细", index=False)
    except: sys.exit(1)

if __name__ == "__main__":
    main()
