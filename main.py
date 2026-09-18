import os
import requests
from datetime import datetime, timedelta

K = os.environ.get("API_FOOTBALL_KEY")
T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")

HEADERS = {
    "x-apisports-key": K
}

LEAGUES = {
    39: "英超",
    140: "西甲",
    135: "意甲",
    78: "德甲",
    61: "法甲",
    2: "欧冠"
}

def send(msg):
    if not T or not C:
        return
    url = f"https://api.telegram.org/bot{T}/sendMessage"
    
    if len(msg) > 3800:
        lines, cur = msg.split("\n"), ""
        for line in lines:
            if len(cur) + len(line) + 1 > 3800:
                requests.post(url, json={"chat_id": C, "text": cur})
                cur = line
            else:
                cur = (cur + "\n" + line) if cur else line
        if cur:
            requests.post(url, json={"chat_id": C, "text": cur})
    else:
        requests.post(url, json={"chat_id": C, "text": msg})

def get_all_odds_map_for_date(date_str):
    """一次性拉取当天所有比赛的赔率，解决频控问题"""
    url = f"https://v3.football.api-sports.io/odds?date={date_str}"
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200:
        return {}
    
    data = r.json().get("response", [])
    odds_map = {}
    
    for entry in data:
        fid = entry.get("fixture", {}).get("id")
        if not fid:
            continue
            
        bookmakers = entry.get("bookmakers", [])
        h2h, ah, over_under = "", "", ""
        
        # 遍历所有博彩公司，尽可能补充齐 欧赔、亚盘、大小球
        for bm in bookmakers:
            for bet in bm.get("bets", []):
                bet_id = bet.get("id")
                values = bet.get("values", [])
                
                # 1. 欧赔 ( Match Winner / 1X2 )
                if bet_id == 1 and not h2h:
                    hp = next((v["odd"] for v in values if v["value"] == "Home"), "-")
                    dp = next((v["odd"] for v in values if v["value"] == "Draw"), "-")
                    ap = next((v["odd"] for v in values if v["value"] == "Away"), "-")
                    h2h = f"胜{hp} 平{dp} 负{ap}"
                    
                # 2. 亚盘 ( Asian Handicap )
                elif (bet_id == 8 or bet_id == 15) and not ah:
                    h_opt = next((v for v in values if "Home" in str(v.get("value"))), None)
                    a_opt = next((v for v in values if "Away" in str(v.get("value"))), None)
                    if h_opt and a_opt:
                        ah = f"主{h_opt.get('value')}({h_opt.get('odd')}) / 客({a_opt.get('odd')})"
                        
                # 3. 大小球 ( Goals Over/Under )
                elif (bet_id == 5 or bet_id == 6) and not over_under:
                    o_opt = next((v for v in values if "Over" in str(v.get("value"))), None)
                    u_opt = next((v for v in values if "Under" in str(v.get("value"))), None)
                    if o_opt and u_opt:
                        over_under = f"{o_opt.get('value')}球 (大{o_opt.get('odd')}/小{u_opt.get('odd')})"
        
        parts = []
        if h2h: parts.append(f"欧: {h2h}")
        if ah: parts.append(f"亚: {ah}")
        if over_under: parts.append(f"大小: {over_under}")
        
        if parts:
            odds_map[fid] = "  └ " + " | ".join(parts)
            
    return odds_map
def main():
    today = datetime.now()
    dates_to_check = [
        today.strftime("%Y-%m-%d"),
        (today + timedelta(days=1)).strftime("%Y-%m-%d")
    ]
    
    res = ["⚽【各大联赛赛程与完整盘口赔率】"]
    has_match = False
    
    for d in dates_to_check:
        # 1. 获取当天所有比赛
        f_url = f"https://v3.football.api-sports.io/fixtures?date={d}"
        r = requests.get(f_url, headers=HEADERS)
        if r.status_code != 200:
            continue
            
        fixtures = r.json().get("response", [])
        
        # 2. 获取当天批量赔率
        odds_map = get_all_odds_map_for_date(d)
        
        day_matches = {}
        for item in fixtures:
            lid = item.get("league", {}).get("id")
            if lid in LEAGUES:
                fid = item["fixture"]["id"]
                league_name = LEAGUES[lid]
                home = item["teams"]["home"]["name"]
                away = item["teams"]["away"]["name"]
                status = item["fixture"]["status"]["short"]
                
                gh = item["goals"]["home"]
                ga = item["goals"]["away"]
                score = f"{gh}-{ga}" if gh is not None else "未开赛"
                
                # 匹配赔率，若没有则显示未开盘
                odds_info = odds_map.get(fid, "  └ 赔率: 暂未开盘或数据缺失")
                match_block = f"• {home} {score} {away} ({status})\n{odds_info}"
                
                if league_name not in day_matches:
                    day_matches[league_name] = []
                day_matches[league_name].append(match_block)
                has_match = True
                
        if day_matches:
            res.append(f"\n📅 **日期: {d}**")
            for lname, m_list in day_matches.items():
                res.append(f"\n🏆 **{lname}**")
                res.extend(m_list)
                
    if not has_match:
        res.append("\n今明两天暂无关注联赛的比赛安排。")
        
    send("\n".join(res))

if __name__ == "__main__":
    main()
    print("推送完成！")
