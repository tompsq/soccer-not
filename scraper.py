import os
import sys
import time
import json
import requests
from datetime import datetime

# 获取今天日期的字符串 (例如: 2026-10-10)
TODAY_STR = datetime.today().strftime('%Y-%m-%d')
BASE_API = "https://sofascore.com"

def fetch_via_proxy(target_url, api_key):
    """通用代理请求函数，专门破解 Cloudflare 403 拦截"""
    proxy_url = f"https://zenrows.com{api_key}&url={target_url}&js_render=true&premium_proxy=true"
    try:
        response = requests.get(proxy_url, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"API 请求失败，状态码: {response.status_code}，链接: {target_url}")
            return None
    except Exception as e:
        print(f"请求发生异常: {e}")
        return None

def main():
    # 1. 从 GitHub 变量中读取你刚刚绑定的密钥
    API_KEY = os.environ.get("ANTI_BOT_KEY", "")
    if not API_KEY:
        print("❌ 错误：未在 GitHub Secrets 中检测到 ANTI_BOT_KEY！请检查绑定是否成功。")
        sys.exit(1)
        
    print(f"🚀 开始抓取日期 {TODAY_STR} 的 SofaScore 足球核心特征库...")

    # 2. 抓取今日赛程列表，获取 event_id
    schedule_url = f"{BASE_API}/sport/football/scheduled-events/{TODAY_STR}"
    schedule_data = fetch_via_proxy(schedule_url, API_KEY)
    
    if not schedule_data or "events" not in schedule_data:
        print("❌ 无法获取今日赛程列表，请检查网络或 ZenRows 额度。")
        sys.exit(1)
        
    events = schedule_data.get("events", [])
    print(f"🎉 成功解锁今日赛程！共发现 {len(events)} 场足球比赛。")
    
    # 为了防止单次运行时间过长导致被 GitHub 强制中断，手机端测试先默认精选前 5 场核心比赛进行深度抓取
    test_limit = min(5, len(events))
    print(f"⚡ 正在深度透视前 {test_limit} 场比赛的【赔率 + 交锋 + 伤停】数据...")
    
    ai_dataset = []

    for idx, event in enumerate(events[:test_limit]):
        event_id = event.get("id")
        home_name = event.get("homeTeam", {}).get("name")
        away_name = event.get("awayTeam", {}).get("name")
        print(f" ⏳ [{idx+1}/{test_limit}] 正在穿透解析: {home_name} vs {away_name} (ID: {event_id})")
        
        # 基础比赛字典（作为 AI 模型的行数据）
        match_dict = {
            "match_id": event_id,
            "date": TODAY_STR,
            "tournament": event.get("tournament", {}).get("name"),
            "home_team": home_name,
            "away_team": away_name,
            "odds_data": {},
            "h2h_data": {},
            "lineups_data": {}
        }
        
        # 防止请求太快被 ZenRows 限制速度，每场比赛稍微缓冲 1 秒
        time.sleep(1)
        
        # 3. 顺藤摸瓜抓取数据：盘口赔率 (Odds)
        odds_url = f"{BASE_API}/event/{event_id}/odds/1/all"
        odds_res = fetch_via_proxy(odds_url, API_KEY)
        if odds_res:
            match_dict["odds_data"] = odds_res
            
        # 4. 顺藤摸瓜抓取数据：历史交锋 (H2H)
        h2h_url = f"{BASE_API}/event/{event_id}/h2h"
        h2h_res = fetch_via_proxy(h2h_url, API_KEY)
        if h2h_res:
            match_dict["h2h_data"] = h2h_res
            
        # 5. 顺藤摸瓜抓取数据：首发阵型与伤停名单 (Lineups)
        lineups_url = f"{BASE_API}/event/{event_id}/lineups"
        lineups_res = fetch_via_proxy(lineups_url, API_KEY)
        if lineups_res:
            match_dict["lineups_data"] = lineups_res
            
        ai_dataset.append(match_dict)

    # 6. 将所有大拼图组合好的数据写入文件
    output_filename = "ai_football_ready_data.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(ai_dataset, f, ensure_ascii=False, indent=4)
        
    print(f"🎯 终极数据集构建成功！已保存为: {output_filename}")

if __name__ == "__main__":
    main()
