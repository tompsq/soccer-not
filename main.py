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

def get_odds_for_fixture(fixture_id):
    """获取单场比赛的欧赔、亚盘和大小球"""
    url = f"https://v3.football.api-sports.io/odds?fixture={fixture_id}"
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200:
        return ""
    
    data = r.json().get("response", [])
    if not data or not data[0].get("bookmakers"):
        return "  └ 赔率: 暂未开盘"
        
    bm = data[0]["bookmakers"][0] # 默认取第一个博彩公司数据
    h2h, ah, over_under = "", "", ""
    
    for bet in bm.get("bets", []):
        bet_id = bet.get("id")
        values = bet.get("values", [])
        
        # 1. 欧赔 (1X2)
        if bet_id == 1 and not h2h:
            hp = next((v["odd"] for v in values if v["value"] == "Home"), "-")
            dp = next((v["odd"] for v in values if v["value"] == "Draw"), "-")
            ap = next((v["odd"] for v in values if v["value"] == "Away"), "-")
            h2h = f"欧: {hp} | {dp} | {ap}"
            
        # 2. 亚盘 (Asian Handicap)
        elif bet_id == 8 and not ah:
            h_opt = next((v for v in values if "Home" in str(v["value"])), None)
            a_opt = next((v for v in values if "Away" in str(v["value"])), None)
            if h_opt and a_opt:
                ah = f"亚: 主 {h_opt.get('value')} ({h_opt.get('odd')}) / 客 ({a_opt.get('odd')})"
                
        # 3. 大小球 (Goals Over/Under)
        elif bet_id == 5 and not over_under:
            o_opt = next((v for v in values if "Over" in str(v["value"])), None)
            u_opt = next((v for v in values if "Under" in str(v["value"])), None)
            if o_opt and u_opt:
                over_under = f"球: {o_opt.get('value')} (大 {o_opt.get('odd')} / 小 {u_opt.get('odd')})"
                
    odds_parts = [p for p in [h2h, ah, over_under] if p]
    if odds_parts:
        return "  └ " + " | ".join(odds_parts)
    return "  └ 赔率: 未匹配到主要盘口"

def main():
    today = datetime.now()
    dates_to_check = [
        today.strftime("%Y-%m-%d"),
        (today + timedelta(days=1)).strftime("%Y-%m-%d")
    ]
    
    res = ["⚽【热门足球联赛赛程与赔率盘口】"]
    has_match = False
    
    for d in dates_to_check:
        url = f"https://v3.football.api-sports.io/fixtures?date={d}"
        r = requests.get(url, headers=HEADERS)
        if r.status_code != 200:
            continue
            
        fixtures = r.json().get("response", [])
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
                
                # 只有未开赛或刚开赛的请求赔率，节省 API 请求
                odds_str = ""
                if status in ["NS", "TBD", "1H", "HT"]:
                    odds_str = get_odds_for_fixture(fid)
                
                match_block = f"• {home} {score} {away} ({status})\n{odds_str}".strip()
                
                if league_name not in day_matches:
                    day_matches[league_name] = []
                day_matches[league_name].append(match_block)
                has_match = True
                
        if day_matches:
            res.append(f"\n📅 **日期: {d}**")
            for lname, m_list in day_matches.items():
                res.append(f"\n🏆 {lname}")
                res.extend(m_list)
                
    if not has_match:
        res.append("\n今明两天暂无关注联赛的比赛安排。")
        
    send("\n".join(res))

if __name__ == "__main__":
    main()
    print("推送完成！")
