import os, requests
from datetime import datetime, timezone, timedelta

T, C = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")

# 关注的联赛列表及名称
LEAGUES = {
    "ENG-Premier League": "英超",
    "ESP-La Liga": "西甲",
    "ITA-Serie A": "意甲",
    "GER-Bundesliga": "德甲",
    "FRA-Ligue 1": "法甲"
}

def send(msg):
    if not T or not C: return
    url = f"https://api.telegram.org/bot{T}/sendMessage"
    if len(msg) > 3800:
        for i in range(0, len(msg), 3800):
            requests.post(url, json={"chat_id": C, "text": msg[i:i+3800]})
    else:
        requests.post(url, json={"chat_id": C, "text": msg})

def get_completed_scores():
    # 这里我们使用公开稳定的体育赛事比分聚合接口获取近期完场结果
    url = "https://www.thesportsdb.com/api/v1/json/3/eventsday.php"
    # 或者获取近期赛果的通用逻辑
    # 鉴于我们需要周二看上一轮完场，通常可以请求近期已结束的赛事数据
    tz = timezone(timedelta(hours=8))
    today_str = datetime.now(tz).strftime("%Y-%m-%d")
    
    # 实际生产中，我们可以调取免费的公开赛果 API
    # 这里为你写好基础框架结构：
    res = ["====================\n⚽ 上周完场比分汇总 (免费获取)\n===================="]
    
    # 示例占位（后续可直接对接稳定的免费赛果 JSON 源）
    res.append("正在获取各大联赛上一轮完场比分...\n（该模块不消耗任何 Odds API 额度）")
    
    return "\n".join(res)

def main():
    msg = get_completed_scores()
    send(msg)

if __name__ == "__main__":
    main()
