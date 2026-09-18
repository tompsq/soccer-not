import os
import requests
from datetime import datetime

ODDS_KEY = os.environ.get("ODDS_API_KEY")
T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")

# 11 个目标联赛配置
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
    
    # 按照 Telegram 限制拆分长消息
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
    """格式化让球盘描述"""
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

def get_league_odds_formatted(sport_key, league_name):
    """调用 The Odds API 抓取指定联赛的欧赔、亚盘、大小球，并进行排版"""
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/"
    params = {
        "apiKey": ODDS_KEY,
        "regions": "eu,uk",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "decimal"
    }
    
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            return {}
            
        data = r.json()
        date_groups = {}
        
        for match in data:
            home = match.get("home_team")
            away = match.get("away_team")
            
            # 解析时间 -> 日期 (D/M/YYYY) 与 时间 (HH:MM)
            raw_time = match.get("commence_time", "")
            if len(raw_time) >= 16:
                dt = datetime.strptime(raw_time[:16], "%Y-%m-%dT%H:%M")
                formatted_date = f"{dt.day}/{dt.month}/{dt.year}"
                time_str = dt.strftime("%H:%M")
            else:
                formatted_date = "近期"
                time_str = "00:00"
            
            bookmakers = match.get("bookmakers", [])
            if not bookmakers:
                continue
                
            bm = bookmakers[0]
            h2h_str, ah_str, totals_str = "", "", ""
            
            for market in bm.get("markets", []):
                m_key = market.get("key")
                outcomes = market.get("outcomes", [])
                
                # 1. 欧赔 (h2h)
                if m_key == "h2h":
                    hp = next((o["price"] for o in outcomes if o["name"] == home), "-")
                    dp = next((o["price"] for o in outcomes if o["name"] == "Draw"), "-")
                    ap = next((o["price"] for o in outcomes if o["name"] == away), "-")
                    h2h_str = f"{hp} {dp} {ap}"
                    
                # 2. 亚盘让球 (spreads)
                elif m_key == "spreads":
                    h_opt = next((o for o in outcomes if o["name"] == home), None)
                    a_opt = next((o for o in outcomes if o["name"] == away), None)
                    if h_opt and a_opt:
                        point = h_opt.get("point", 0)
                        label = format_handicap_label(point)
                        ah_str = f"{label} (主){h_opt.get('price')} (客){a_opt.get('price')}"
                        
                # 3. 大小球 (totals)
                elif m_key == "totals":
                    o_opt = next((o for o in outcomes if o["name"] == "Over"), None)
                    u_opt = next((o for o in outcomes if o["name"] == "Under"), None)
                    if o_opt and u_opt:
                        point = o_opt.get("point", "-")
                        totals_str = f"{point} (大){o_opt.get('price')} (小){u_opt.get('price')}"
            
            lines = []
            if h2h_str: lines.append(h2h_str)
            if ah_str: lines.append(ah_str)
            if totals_str: lines.append(totals_str)
            
            odds_block = "\n".join(lines) if lines else "暂无盘口"
            match_text = f"{time_str}\n{home} vs {away}\n{odds_block}"
            
            if formatted_date not in date_groups:
                date_groups[formatted_date] = []
            date_groups[formatted_date].append(match_text)
            
        return date_groups
    except Exception as e:
        print(f"获取 {league_name} 出错: {e}")
        return {}
main():
    if not ODDS_KEY:
        send("❌ 错误：未读取到 ODDS_API_KEY，请检查 GitHub Secrets 配置！")
        return

    res = []
    
    for sport_key, league_name in SPORT_KEYS.items():
        date_groups = get_league_odds_formatted(sport_key, league_name)
        
        for date_str, match_list in date_groups.items():
            res.append(f"{league_name} {date_str}\n")
            res.append("\n\n".join(match_list))
            res.append("\n" + "="*20 + "\n")
            
    if not res:
        send("近期 11 个指定联赛暂无开盘数据。")
    else:
        send("\n".join(res))

if __name__ == "__main__":
    main()
    print("推送完成！")        
