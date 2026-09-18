def get_past_results(sport_key, league_name):
    """抓取过去 6 天的完场比分"""
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/scores/"
    params = {"apiKey": ODDS_KEY, "daysFrom": 6}
    
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
def get_league_odds_formatted(sport_key, league_name, only_today=False):
    """抓取盘口赔率"""
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/"
    params = {
        "apiKey": ODDS_KEY,
        "regions": "eu,uk,us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "decimal"
    }
    
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200 or not r.json():
            return {}
            
        data = r.json()
        date_groups = {}
        tz_utc8 = timezone(timedelta(hours=8))
        now_utc8 = datetime.now(tz_utc8)
        today_str = f"{now_utc8.day}/{now_utc8.month}/{now_utc8.year}"
        tomorrow_str = f"{(now_utc8 + timedelta(days=1)).day}/{(now_utc8 + timedelta(days=1)).month}/{(now_utc8 + timedelta(days=1)).year}"

        for match in data:
            home, away = match.get("home_team"), match.get("away_team")
            raw_time = match.get("commence_time", "")
            
            if len(raw_time) >= 19:
                utc_dt = datetime.strptime(raw_time[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                local_dt = utc_dt.astimezone(tz_utc8)
                formatted_date = f"{local_dt.day}/{local_dt.month}/{local_dt.year}"
                time_str = local_dt.strftime("%H:%M")
            else:
                formatted_date, time_str = "近期赛程", "00:00"
            
            if only_today and formatted_date not in [today_str, tomorrow_str]:
                continue

            bookmakers = match.get("bookmakers", [])
            if not bookmakers: continue
                
            h2h_str, ah_str, totals_str = "", "", ""
            for bm in bookmakers:
                for market in bm.get("markets", []):
                    m_k, outcomes = market.get("key"), market.get("outcomes", [])
                    
                    if m_k == "h2h" and not h2h_str:
                        hp = next((o["price"] for o in outcomes if o["name"] == home), "-")
                        dp = next((o["price"] for o in outcomes if o["name"] == "Draw"), "-")
                        ap = next((o["price"] for o in outcomes if o["name"] == away), "-")
                        h2h_str = f"{hp} {dp} {ap}"
                        
                    elif m_k == "spreads" and not ah_str:
                        h_opt = next((o for o in outcomes if o["name"] == home), None)
                        a_opt = next((o for o in outcomes if o["name"] == away), None)
                        if h_opt and a_opt:
                            ah_str = f"{format_handicap_label(h_opt.get('point', 0))} (主){h_opt.get('price')} (客){a_opt.get('price')}"
                            
                    elif m_k == "totals" and not totals_str:
                        o_opt = next((o for o in outcomes if o["name"] == "Over"), None)
                        u_opt = next((o for o in outcomes if o["name"] == "Under"), None)
                        if o_opt and u_opt:
                            totals_str = f"{o_opt.get('point', '-')} (大){o_opt.get('price')} (小){u_opt.get('price')}"
            
            lines = [s for s in [h2h_str, ah_str, totals_str] if s]
            odds_block = "\n".join(lines) if lines else "暂无完整盘口"
            match_text = f"{time_str}\n{home} vs {away}\n{odds_block}"
            
            date_groups.setdefault(formatted_date, []).append(match_text)
            
        return date_groups
    except Exception as e:
        print(f"抓取 {league_name} 盘口失败: {e}")
        return {}
if __name__ == "__main__":
    main()
