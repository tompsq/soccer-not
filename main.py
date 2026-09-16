import os
import requests
from datetime import datetime, timezone, timedelta

# 1. 获取环境变量
ODDS_API_KEY = os.environ.get("ODDS_API_KEY")
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")

# 定义你要监控的 11 个联赛及其在 The Odds API 中的代号（已加入英冠）
LEAGUES = {
    "英超": "soccer_epl",
    "英冠": "soccer_efl_champ",
    "西甲": "soccer_spain_la_liga",
    "意甲": "soccer_italy_serie_a",
    "德甲": "soccer_germany_bundesliga",
    "欧冠": "soccer_uefa_champs_league",
    "欧联杯": "soccer_uefa_europa_league",
    "葡超": "soccer_portugal_primeira_liga",
    "苏超": "soccer_spl",
    "荷甲": "soccer_netherlands_eredivisie",
    "希超": "soccer_greece_super_league"
}

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    if len(message) > 4000:
        message = message[:4000] + "\n...(内容过长已截断)"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)

def fetch_all_leagues_odds():
    message_lines = ["⚽ *各大主流联赛最新赔率播报* ⚽\n"]
    
    for name, key in LEAGUES.items():
        url = f"https://api.the-odds-api.com/v4/sports/{key}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h"
        response = requests.get(url)
        if response.status_code != 200:
            continue
        
        data = response.json()
        if not data or not isinstance(data, list):
            continue
            
        message_lines.append(f"🏆 *【{name}】*")
        for match in data[:2]:
            home = match.get("home_team", "主队")
            away = match.get("away_team", "客队")
            commence_time = match.get("commence_time", "").replace("T", " ")[:16]
            
            message_lines.append(f"  • *{home} vs {away}* (`{commence_time}`)")
            bookmakers = match.get("bookmakers", [])
            if bookmakers:
                markets = bookmakers[0].get("markets", [])
                for market in markets:
                    if market.get("key") == "h2h":
                        outcomes = market.get("outcomes", [])
                        odds_str = " | ".join([f"{o.get('name')}: `{o.get('price')}`" for o in outcomes])
                        message_lines.append(f"    💰 {odds_str}")
        message_lines.append("")
        
    return "\n".join(message_lines)

def fetch_recent_scores():
    message_lines = ["📊 *各大联赛近期完场比分汇总* 📊\n"]
    
    for name, key in LEAGUES.items():
        url = f"https://api.the-odds-api.com/v4/sports/{key}/scores/?apiKey={ODDS_API_KEY}&daysFrom=3"
        response = requests.get(url)
        if response.status_code != 200:
            continue
            
        data = response.json()
        if not data or not isinstance(data, list):
            continue
            
        completed_matches = [m for m in data if m.get("completed") == True]
        if not completed_matches:
            continue
            
        message_lines.append(f"🏆 *【{name} 完场比分】*")
        for match in completed_matches[:3]:
            home = match.get("home_team", "主队")
            away = match.get("away_team", "客队")
            scores = match.get("scores", [])
            
            home_score = "0"
            away_score = "0"
            if scores:
                for s in scores:
                    if s.get("name") == home:
                        home_score = s.get("score", "0")
                    elif s.get("name") == away:
                        away_score = s.get("score", "0")
            
            message_lines.append(f"  ✅ *{home} {home_score} - {away_score} {away}*")
        message_lines.append("")
        
    return "\n".join(message_lines)

if __name__ == "__main__":
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc + timedelta(hours=8)
    
    print(f"当前本地时间: {now_local.strftime('%Y-%m-%d %H:%M:%S')} (星期{now_local.weekday()+1})")
    print("正在获取多联赛赔率与完场比分...")
    
    odds_content = fetch_all_leagues_odds()
    scores_content = fetch_recent_scores()
    
    final_message = scores_content + "\n\n-----------------------------------\n\n" + odds_content
    
    print("推送到 Telegram...")
    send_telegram_message(final_message)
    print("推送完成！")
