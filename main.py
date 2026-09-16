import os
import requests
from datetime import datetime, timezone, timedelta

# 1. 获取环境变量
ODDS_API_KEY = os.environ.get("ODDS_API_KEY")
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")

# 监控的 11 个联赛代号
LEAGUES = {
    "英超": "soccer_epl",
    "英冠": "soccer_efl_champ",
    "西甲": "soccer_spain_la_liga",
    "意甲": "soccer_italy_serie_a",
    "德甲": "soccer_germany_bundesliga",
    "欧冠": "soccer_uefa_champs_league",
    "欧联杯": "soccer_uefa_europa_league",
    "葡超": "soccer_portugal_primeira_liga",
    "荷甲": "soccer_netherlands_eredivisie",
    "苏超": "soccer_spl",
    "希超": "soccer_greece_super_league"
}

# 常见球队名称精简映射
TEAM_MAP = {
    "Manchester City": "曼城", "Manchester United": "曼联", "Arsenal": "阿森纳",
    "Liverpool": "利物浦", "Chelsea": "切尔西", "Tottenham Hotspur": "热刺",
    "Aston Villa": "维拉", "Newcastle United": "纽卡", "Brighton": "布莱顿",
    "Real Madrid": "皇马", "Barcelona": "巴萨", "Atletico Madrid": "马竞",
    "Bayern Munich": "拜仁", "Borussia Dortmund": "多特", "Bayer Leverkusen": "勒沃库森",
    "Inter Milan": "国米", "AC Milan": "AC米兰", "Juventus": "尤文", "Napoli": "那不勒斯",
    "Paris Saint-Germain": "巴黎", "Marseille": "马赛"
}

def short_name(name):
    return TEAM_MAP.get(name, name)

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    
    # 超过 3800 字符自动分段发送
    if len(message) > 3800:
        lines = message.split("\n")
        chunks = []
        current_chunk = ""
        for line in lines:
            if len(current_chunk) + len(line) + 1 > 3800:
                chunks.append(current_chunk)
                current_chunk = line
            else:
                current_chunk = (current_chunk + "\n" + line) if current_chunk else line
        if current_chunk:
            chunks.append(current_chunk)
            
        for chunk in chunks:
            payload = {
                "chat_id": TG_CHAT_ID,
                "text": chunk,
                "parse_mode": "Markdown"
            }
            requests.post(url, json=payload)
    else:
        payload = {
            "chat_id": TG_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload)

def fetch_all_leagues_odds():
    lines = ["赔率"]
    
    for name, key in LEAGUES.items():
        url = f"https://api.the-odds-api.com/v4/sports/{key}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h,spreads"
        response = requests.get(url)
        if response.status_code != 200:
            continue
        
        data = response.json()
        if not data or not isinstance(data, list):
            continue
            
        league_blocks = []
        for match in data[:10]:
            home = short_name(match.get("home_team", ""))
            away = short_name(match.get("away_team", ""))
            bookmakers = match.get("bookmakers", [])
            
            h2h_str = ""
            spread_str = ""
            
            if bookmakers:
                markets = bookmakers[0].get("markets", [])
                for m in markets:
                    m_key = m.get("key")
                    outcomes = m.get("outcomes", [])
                    if m_key == "h2h" and len(outcomes) == 3:
                        h2h_str = f"{outcomes[0].get('price')} {outcomes[1].get('price')} {outcomes[2].get('price')}"
                    elif m_key == "spreads" and len(outcomes) == 2:
                        point = outcomes[0].get("point")
                        p_str = f"{point:+g}" if point is not None else ""
                        spread_str = f"{p_str} {outcomes[0].get('price')} {outcomes[1].get('price')}"
            
            if home and away and h2h_str:
                match_lines = [f"{home} vs {away}", h2h_str]
                if spread_str:
                    match_lines.append(spread_str)
                league_blocks.append("\n".join(match_lines))
        
        if league_blocks:
            lines.append(f"\n{name}")
            lines.extend(league_blocks)
        
    return "\n".join(lines)

def fetch_recent_scores():
    lines = ["完场比分"]
    
    for name, key in LEAGUES.items():
        url = f"https://api.the-odds-api.com/v4/sports/{key}/scores/?apiKey={ODDS_API_KEY}&daysFrom=3"
        response = requests.get(url)
        if response.status_code != 200:
            continue
            
        data = response.json()
        if not data or not isinstance(data, list):
            continue
            
        completed = [m for m in data if m.get("completed") == True]
        if not completed:
            continue
            
        league_scores = []
        for match in completed[:10]:
            home = short_name(match.get("home_team", ""))
            away = short_name(match.get("away_team", ""))
            scores = match.get("scores", [])
            
            h_score, a_score = "0", "0"
            if scores:
                for s in scores:
                    if short_name(s.g
