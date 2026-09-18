import os
import requests
from datetime import datetime, timezone, timedelta

ODDS_KEY = os.environ.get("ODDS_API_KEY")
T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")

# 11 个目标联赛
SPORT_KEYS = {
    "soccer_epl": "英超",
    "soccer_spain_la_liga": "西甲",
    "soccer_italy_serie_a": "意甲",
    "soccer_germany_bundesliga": "德甲",
    "soccer_france_ligue_one": "法甲",
    "soccer_uefa_champs_league": "欧冠",
    "soccer_uefa_europa_conference_league": "欧联/欧协联",
    "soccer_portugal_primeira_liga": "葡超",
    "soccer_spl": "苏超",
    "soccer_belgium_first_div": "比甲",
    "soccer_greece_super_league": "希超"
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

def format_handicap_label(point):
    """格式化让球盘标签"""
    try:
        val = float(point)
        if val == 0:
            return "平盘"
        elif val < 0:
            return f"主{val}"
        else:
            return f"客-{val}"
    except:
        return str(point)

def get_past_results(sport_key, league_name):
    """抓取过去 6 天的完场比分"""
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/scores/"
    params = {
        "apiKey": ODDS_KEY,
        "daysFrom": 6
    }
    
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            return {}
            
        data = r.json()
        date_groups = {}
        tz_utc8 = timezone(timedelta(hours=8))
        
        for match in data:
            if not match.get("completed"):
                continue
                
            home = match.get("home_team")
            away = match.get("away_team")
            scores = match.get("scores")
            
            score_str = "完场 比分未知"
            if scores and len(scores) >= 2:
                h_score = next((s["score"] for s in scores if s["name"] == home), "-")
                a_score = next((s["score"] for s in scores if s["name"] == away), "-")
                score_str = f"完场 {h_score} : {a_score}"
                
            raw_time = match.get("commence_time", "")
            if len(raw_time) >= 19:
                utc_dt = datetime.strptime(raw_time[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                local_dt = utc_dt.astimezone(tz_utc8)
                formatted_date = f"{local_dt.day}/{local_dt.month}/{local_dt.year}"
                time_str = local_dt.strftime("%H:%M")
            else:
                formatted_date = "近期完场"
                time_str = "00:00"
                
            match_text = f"{time_str}\n{home} vs {away}\n{score_str}"
            
            if formatted_date not in date_groups:
                date_groups[formatted_date] = []
            date_groups[formatted_date].append(match_text)
            
        return date_groups
    except Exception as e:
        print(f"抓取 {league_name} 比分失败: {e}")
        return {}
def get_league_odds_formatted(sport_key, league_name):
    """抓取所有已开盘赛事的早盘盘口与赔率"""
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/"
    params = {
        "apiKey": ODDS_KEY,
        "regions": "eu,uk,us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "decimal"
    }
    
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            return {}
            
        data = r.json()
        if not data:
            return {}
            
        date_groups = {}
        tz_utc8 = timezone(timedelta(hours=8))
        
        for match in data:
            home = match.get("home_team")
            away = match.get("away_team")
            
            raw_time = match.get("commence_time", "")
            if len(raw_time) >= 19:
                utc_dt = datetime.strptime(raw_time[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                local_dt = utc_dt.astimezone(tz_utc8)
                formatted_date = f"{local_dt.day}/{local_dt.month}/{local_dt.year}"
                time_str = local_dt.strftime("%H:%M")
            else:
                formatted_date = "近期赛程"
                time_str = "00:00"
            
            bookmakers = match.get("bookmakers", [])
            if not bookmakers:
                continue
                
            h2h_str, ah_str, totals_str = "", "", ""
            
            for bm in bookmakers:
                for market in bm.get("markets", []):
                    m_key = market.get("key")
                    outcomes = market.get("outcomes", [])
                    
                    if m_key == "h2h" and not h2h_str:
                        hp = next((o["price"] for o in outcomes if o["name"] == home), "-")
                        dp = next((o["price"] for o in outcomes if o["name"] == "Draw"), "-")
                        ap = next((o["price"] for o in outcomes if o["name"] == away), "-")
                        h2h_str = f"{hp} {dp} {ap}"
                        
                    elif m_key == "spreads" and not ah_str:
                        h_opt = next((o for o in outcomes if o["name"] == home), None)
                        a_opt = next((o for o in outcomes if o["name"] == away), None)
                        if h_opt and a_opt:
                            point = h_opt.get("point", 0)
                            label = format_handicap_label(point)
                            ah_str = f"{label} (主){h_opt.get('price')} (客){a_opt.get('price')}"
                            
                    elif m_key == "totals" and not totals_str:
                        o_opt = next((o for o in outcomes if o["name"] == "Over"), None)
                        u_opt = next((o for o in outcomes if o["name"] == "Under"), None)
                        if o_opt and u_opt:
                            point = o_opt.get("point", "-")
                            totals_str = f"{point} (大){o_opt.get('price')} (小){u_opt.get('price')}"
            
            lines = []
            if h2h_str: lines.append(h2h_str)
            if ah_str: lines.append(ah_str)
            if totals_str: lines.append(totals_str)
            
            odds_block = "\n".join(lines) if lines else "暂无完整盘口"
            match_text = f"{time_str}\n{home} vs {away}\n{odds_block}"
            
            if formatted_date not in date_groups:
                date_groups[formatted_date] = []
            date_groups[formatted_date].append(match_text)
            
        return date_groups
    except Exception as e:
        print(f"抓取 {league_name} 盘口失败: {e}")
        return {}

def main():
    if not ODDS_KEY:
        send("❌ 错误：未读取到 ODDS_API_KEY！")
        return

    res = []
    
    # 1. 完场比分 (周三至周一)
    res.append("====================\n🏆 过去 6 天完场比分\n====================")
    has_results = False
    for sport_key, league_name in SPORT_KEYS.items():
        results_groups = get_past_results(sport_key, league_name)
        for date_str, match_list in results_groups.items():
            has_results = True
            res.append(f"{league_name} {date_str} (完场)\n")
            res.append("\n\n".join(match_list))
            res.append("\n" + "-"*15 + "\n")
            
    if not has_results:
        res.append("近期无已结算完场比分。\n")
        
    # 2. 所有联赛已开盘赛事的早盘盘口
    res.append("====================\n⚽ 全联赛早盘赛程与盘口\n====================")
    has_odds = False
    for sport_key, league_name in SPORT_KEYS.items():
        odds_groups = get_league_odds_formatted(sport_key, league_name)
        for date_str, match_list in odds_groups.items():
            has_odds = True
            res.append(f"{league_name} {date_str}\n")
            res.append("\n\n".join(match_list))
            res.append("\n" + "-"*15 + "\n")
            
    if not has_odds:
        res.append("近期暂无开盘赛程。\n")
        
    send("\n".join(res))

if __name__ == "__main__":
    main()
