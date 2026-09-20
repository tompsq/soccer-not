import os, requests
from datetime import datetime, timezone, timedelta

T, C = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")

def send(msg):
    if not T or not C: return
    url = f"https://api.telegram.org/bot{T}/sendMessage"
    if len(msg) > 3800:
        for i in range(0, len(msg), 3800):
            requests.post(url, json={"chat_id": C, "text": msg[i:i+3800]})
    else:
        requests.post(url, json={"chat_id": C, "text": msg})

def get_free_scores():
    # 使用无需Key的免费足球赛事/比分公开数据源 (例如 free-football-data 或类似公开接口)
    # 这里以 football-data.org 的免费公开档位 或 聚合公开比分接口为例
    try:
        # 示例：获取近期完场比赛
        url = "https://www.thesportsdb.com/api/v1/json/3/eventsday.php?d=" + (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        r = requests.get(url, timeout=10)
        data = r.json()
        
        events = data.get("events")
        if not events:
            return "⚽ 昨夜今晨暂无完场比赛记录。"
        
        res = ["====================\n⚽ 免费完场比分汇总 (白嫖版)\n===================="]
        for ev in events:
            league = ev.get("strLeague", "")
            home = ev.get("strHomeTeam", "")
            away = ev.get("strAwayTeam", "")
            h_score = ev.get("intHomeScore", "-")
            a_score = ev.get("intAwayScore", "-")
            status = ev.get("strStatus", "")
            
            # 只看已完场的比赛
            if status in ["FT", "AET", "Pen", "Finished"] or (h_score and h_score != "None"):
                res.append(f"【{league}】\n{home} {h_score} - {a_score} {away}\n" + "-"*15)
                
        return "\n".join(res) if len(res) > 1 else "近期暂无已完场比赛。"
    except Exception as e:
        return f"❌ 获取比分异常：{str(e)}"

def main():
    msg = get_free_scores()
    send(msg)

if __name__ == "__main__":
    main()
