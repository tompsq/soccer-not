import os, requests
from datetime import datetime, timezone, timedelta

ODDS_KEY, T, C = os.environ.get("ODDS_API_KEY"), os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")

# 💡 手机调试开关：
# True = 使用内置假数据（绝对不耗 API 额度，随时在手机上点运行看效果）
# False = 正式请求 API（晚上比赛多的时候用）
USE_MOCK = True 

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
        for i in range(0, len(msg), 3800):
            requests.post(url, json={"chat_id": C, "text": msg[i:i+3800]})
    else: requests.post(url, json={"chat_id": C, "text": msg})

def format_handicap_label(p):
    try:
        v = float(p)
        return "平盘" if v == 0 else (f"主{v}" if v < 0 else f"客-{v}")
    except: return str(p)

def get_near_future_odds(sport_key, league_name):
    try:
        if USE_MOCK:
            data = [{
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "commence_time": "2026-09-20T14:00:00Z",
                "bookmakers": [{
                    "key": "pinnacle",
                    "markets": [
                        {"key": "h2h", "outcomes": [{"name": "Arsenal", "price": 1.85}, {"name": "Draw", "price": 3.5}, {"name": "Chelsea", "price": 4.2}]},
                        {"key": "spreads", "outcomes": [{"name": "Arsenal", "price": 1.95, "point": -0.75}, {"name": "Chelsea", "price": 1.85, "point": 0.75}]},
                        {"key": "totals", "outcomes": [{"name": "Over", "price": 1.9, "point": 2.5}, {"name": "Under", "price": 1.9, "point": 2.5}]}
                    ]
                }]
            }]
        else:
            url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/"
            r = requests.get(url, params={"apiKey": ODDS_KEY, "regions": "eu,uk,us", "markets": "h2h,spreads,totals", "oddsFormat": "decimal"}, timeout=10)
            if r.status_code != 200 or not r.json(): return {}
            data = r.json()
        date_groups, tz = {}, timezone(timedelta(hours=8))
        now_local = datetime.now(tz)
        two_hours_later = now_local + timedelta(hours=2)

        for m in data:
            home, away, raw = m.get("home_team"), m.get("away_team"), m.get("commence_time", "")
            if len(raw) >= 19:
                dt = datetime.strptime(raw[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).astimezone(tz)
                fd, ts = f"{dt.day}/{dt.month}/{dt.year}", dt.strftime("%H:%M")
            else: 
                continue
            
            # 如果在 Mock 测试阶段，可以先把下面这行过滤注释掉（在前面加 #），确保能稳定收到测试消息；
            # 等晚上正式用 API 时，再把 # 去掉。
            # if not (now_local <= dt <= two_hours_later): continue

            bms = m.get("bookmakers", [])
            if not bms: continue
            h2h, ah, tot = "", "", ""
            for bm in bms:
                for mk in bm.get("markets", []):
                    k, outs = mk.get("key"), mk.get("outcomes", [])
                    if k == "h2h" and not h2h:
                        hp = next((o["price"] for o in outs if o["name"] == home), "-")
                        dp = next((o["price"] for o in outs if o["name"] == "Draw"), "-")
                        ap = next((o["price"] for o in outs if o["name"] == away), "-")
                        h2h = f"{hp} {dp} {ap}"
                    elif k == "spreads" and not ah:
                        ho = next((o for o in outs if o["name"] == home), None)
                        ao = next((o for o in outs if o["name"] == away), None)
                        if ho and ao: ah = f"{format_handicap_label(ho.get('point', 0))} (主){ho.get('price')} (客){ao.get('price')}"
                    elif k == "totals" and not tot:
                        oo = next((o for o in outs if o["name"] == "Over"), None)
                        uo = next((o for o in outs if o["name"] == "Under"), None)
                        if oo and uo: tot = f"{oo.get('point', '-')} (大){oo.get('price')} (小){uo.get('price')}"
            lines = [s for s in [h2h, ah, tot] if s]
            info = f"⏰ 开赛时间: {ts}\n{home} vs {away}\n" + ("\n".join(lines) if lines else "暂无盘口")
            date_groups.setdefault(fd, []).append(info)
        return date_groups
    except Exception as e:
        print(f"Error: {e}")
        return {}

def main():
    res = ["====================\n⚡ 2小时内即将开赛提醒 (测试中)\n===================="]
    has_odds = False
    for sk, ln in SPORT_KEYS.items():
        for ds, ml in get_near_future_odds(sk, ln).items():
            has_odds = True
            res.append(f"{ln} {ds}\n\n" + "\n\n".join(ml) + "\n" + "-"*15 + "\n")
    if not has_odds: res.append("接下来 2 小时内暂无开赛赛事。\n")
    send("\n".join(res))

if __name__ == "__main__":
    main()
