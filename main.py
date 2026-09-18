import os, requests
from datetime import datetime, timezone, timedelta

ODDS_KEY, T, C = os.environ.get("ODDS_API_KEY"), os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")
RUN_MODE = os.environ.get("RUN_MODE", "auto")

SPORT_KEYS = {
    "soccer_epl": "英超", "soccer_spain_la_liga": "西甲", "soccer_italy_serie_a": "意甲",
    "soccer_germany_bundesliga": "德甲", "soccer_france_ligue_one": "法甲",
    "soccer_uefa_champs_league": "欧冠", "soccer_uefa_europa_conference_league": "欧联/欧协联",
    "soccer_portugal_primeira_liga": "葡超", "soccer_spl": "苏超",
    "soccer_belgium_first_div": "比甲", "soccer_greece_super_league": "希超"
}

def send(msg):
    if not T or not C: return
    url = f"https://api.telegram.org/bot{T}/sendMessage"
    if len(msg) > 3800:
        lines, cur = msg.split("\n"), ""
        for line in lines:
            if len(cur) + len(line) + 1 > 3800:
                requests.post(url, json={"chat_id": C, "text": cur})
                cur = line
            else: cur = (cur + "\n" + line) if cur else line
        if cur: requests.post(url, json={"chat_id": C, "text": cur})
    else: requests.post(url, json={"chat_id": C, "text": msg})

def format_handicap_label(point):
    try:
        val = float(point)
        return "平盘" if val == 0 else (f"主{val}" if val < 0 else f"客-{val}")
    except: return str(point)
def get_past_results(sport_key, league_name):
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/scores/"
    try:
        r = requests.get(url, params={"apiKey": ODDS_KEY, "daysFrom": 6}, timeout=10)
        if r.status_code != 200: return {}
        data, date_groups, tz = r.json(), {}, timezone(timedelta(hours=8))
        for match in data:
            if not match.get("completed"): continue
            home, away, scores = match.get("home_team"), match.get("away_team"), match.get("scores")
            score_str = "完场 比分未知"
            if scores and len(scores) >= 2:
                h = next((s["score"] for s in scores if s["name"] == home), "-")
                a = next((s["score"] for s in scores if s["name"] == away), "-")
                score_str = f"完场 {h} : {a}"
            raw_time = match.get("commence_time", "")
            if len(raw_time) >= 19:
                dt = datetime.strptime(raw_time[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).astimezone(tz)
                fmt_date, time_str = f"{dt.day}/{dt.month}/{dt.year}", dt.strftime("%H:%M")
            else: fmt_date, time_str = "近期完场", "00:00"
            date_groups.setdefault(fmt_date, []).append(f"{time_str}\n{home} vs {away}\n{score_str}")
        return date_groups
    except: return {}
    send("\n".join(res))

def get_league_odds_formatted(sport_key, league_name, only_today=False, hours_ahead=None):
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/"
    params = {"apiKey": ODDS_KEY, "regions": "eu,uk,us", "markets": "h2h,spreads,totals", "oddsFormat": "decimal"}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200 or not r.json(): return {}
        data, date_groups, tz = r.json(), {}, timezone(timedelta(hours=8))
        now = datetime.now(tz)
        t_str = f"{now.day}/{now.month}/{now.year}"

        for match in data:
            home, away, raw_time = match.get("home_team"), match.get("away_team"), match.get("commence_time", "")
            if len(raw_time) >= 19:
                dt = datetime.strptime(raw_time[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).astimezone(tz)
                fmt_date, time_str = f"{dt.day}/{dt.month}/{dt.year}", dt.strftime("%H:%M")
            else: 
                dt, fmt_date, time_str = None, "近期赛程", "00:00"
            
            # 过滤逻辑：指定未来 X 小时内
            if hours_ahead is not None:
                if not dt: continue
                # 计算距离开赛的秒数
                diff_sec = (dt - now).total_seconds()
                # 只保留从现在开始到未来 hours_ahead 小时以内的比赛 (0 到 hours_ahead*3600 秒)
                if not (0 <= diff_sec <= hours_ahead * 3600):
                    continue
            elif only_today and fmt_date != t_str:
                continue

            bms = match.get("bookmakers", [])
            if not bms: continue
                
            h2h_s, ah_s, tot_s = "", "", ""
            for bm in bms:
                for market in bm.get("markets", []):
                    mk, outcomes = market.get("key"), market.get("outcomes", [])
                    if mk == "h2h" and not h2h_s:
                        hp = next((o["price"] for o in outcomes if o["name"] == home), "-")
                        dp = next((o["price"] for o in outcomes if o["name"] == "Draw"), "-")
                        ap = next((o["price"] for o in outcomes if o["name"] == away), "-")
                        h2h_s = f"{hp} {dp} {ap}"
                    elif mk == "spreads" and not ah_s:
                        ho, ao = next((o for o in outcomes if o["name"] == home), None), next((o for o in outcomes if o["name"] == away), None)
                        if ho and ao: ah_s = f"{format_handicap_label(ho.get('point', 0))} (主){ho.get('price')} (客){ao.get('price')}"
                    elif mk == "totals" and not tot_s:
                        oo, uo = next((o for o in outcomes if o["name"] == "Over"), None), next((o for o in outcomes if o["name"] == "Under"), None)
                        if oo and uo: tot_s = f"{oo.get('point', '-')} (大){oo.get('price')} (小){uo.get('price')}"
            
            lines = [s for s in [h2h_s, ah_s, tot_s] if s]
            date_groups.setdefault(fmt_date, []).append(f"{time_str}\n{home} vs {away}\n" + ("\n".join(lines) if lines else "暂无盘口"))
        return date_groups
    except: return {}
def main():
    if not ODDS_KEY:
        send("❌ 错误：未读取到 ODDS_API_KEY！")
        return
    res = []
    
    # 模式 1：即将开赛模式（未来 2 小时）
    if RUN_MODE == "upcoming":
        res.append("====================\n⏳ 未来 2 小时即将开赛\n====================")
        has_odds = False
        for sk, ln in SPORT_KEYS.items():
            for ds, ml in get_league_odds_formatted(sk, ln, hours_ahead=2).items():
                has_odds = True
                res.append(f"{ln} {ds}\n\n" + "\n\n".join(ml) + "\n" + "-"*15 + "\n")
        if not has_odds: res.append("未来 2 小时内暂无即将在以上联赛开赛的比赛。\n")
        
    # 模式 2：手动推送全天赛程
    elif RUN_MODE == "manual":
        res.append("====================\n⚡ 当日赛事盘口 (手动即时推送)\n====================")
        has_odds = False
        for sk, ln in SPORT_KEYS.items():
            for ds, ml in get_league_odds_formatted(sk, ln, only_today=True).items():
                has_odds = True
                res.append(f"{ln} {ds}\n\n" + "\n\n".join(ml) + "\n" + "-"*15 + "\n")
        if not has_odds: res.append("今日暂无开盘赛程。\n")
        
    # 模式 3：定时自动完整推送
    else:
        res.append("====================\n🏆 过去 6 天完场比分\n====================")
        has_results = False
        for sk, ln in SPORT_KEYS.items():
            for ds, ml in get_past_results(sk, ln).items():
                has_results = True
                res.append(f"{ln} {ds} (完场)\n\n" + "\n\n".join(ml) + "\n" + "-"*15 + "\n")
        if not has_results: res.append("近期无已结算完场比分。\n")
        
        res.append("====================\n⚽ 全联赛早盘赛程与盘口\n====================")
        has_odds = False
        for sk, ln in SPORT_KEYS.items():
            for ds, ml in get_league_odds_formatted(sk, ln, only_today=False).items():
                has_odds = True
                res.append(f"{ln} {ds}\n\n" + "\n\n".join(ml) + "\n" + "-"*15 + "\n")
        if not has_odds: res.append("近期暂无开盘赛程。\n")
        
    send("\n".join(res))

if __name__ == "__main__":
    main()
