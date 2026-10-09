import os
import sys
import time
import json
import requests
from datetime import datetime

# 自动获取今天的日期 (格式: 2026-10-10)
TODAY_STR = datetime.today().strftime('%Y-%m-%d')
BASE_API = "https://sofascore.com"

def fetch_via_proxy(target_url, raw_key):
    """超级容错且带深度防错诊断的请求函数"""
    # 🧼 洗净手机复制可能产生的多余杂质
    clean_key = str(raw_key).strip().replace("*", "").replace(" ", "").replace("\n", "").replace("\r", "")
    
    proxy_url = "https://zenrows.com"
    query_params = {
        "key": clean_key,
        "url": target_url,
        "js_render": "true",
        "premium_proxy": "true"
    }
    
    try:
        response = requests.get(proxy_url, params=query_params, timeout=30)
        
        # 🩺 【核心诊断】：如果不是200成功，直接打印出服务器返回的真实文本
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ 代理网关返回了错误状态码: {response.status_code}")
            print(f"原始错误提示信息如下:\n{response.text[:500]}")
            return None
            
    except Exception as e:
        print(f"❌ 发生网络联接异常: {e}")
        return None

def main():
    API_KEY = os.environ.get("ANTI_BOT_KEY", "")
    if not API_KEY:
        print("❌ 错误：未在 GitHub Secrets 中检测到 ANTI_BOT_KEY！")
        sys.exit(1)
        
    print(f"🚀 开始抓取日期 {TODAY_STR} 的 SofaScore 足球核心特征库...")

    # 抓取今日赛程列表
    schedule_url = f"{BASE_API}/sport/football/scheduled-events/{TODAY_STR}"
    schedule_data = fetch_via_proxy(schedule_url, API_KEY)
    
    if not schedule_data or "events" not in schedule_data:
        print("\n💡 【手机端排查指南】：")
        print("1. 请去 zenrows.com 后台确认您的 API Key 是否复制完整（不要带任何星号或前后的文字）。")
        print("2. 重新去 GitHub 的 Settings -> Secrets 删掉重建 ANTI_BOT_KEY，确保粘贴进去的是一串三十多位纯粹的字母和数字组合。")
        sys.exit(1)
        
    events = schedule_data.get("events", [])
    print(f"🎉 成功解锁今日赛程！共发现 {len(events)} 场足球比赛。")
    
    test_limit = min(5, len(events))
    ai_dataset = []

    for idx, event in enumerate(events[:test_limit]):
        event_id = event.get("id")
        home_name = event.get("homeTeam", {}).get("name")
        away_name = event.get("awayTeam", {}).get("name")
        print(f" ⏳ [{idx+1}/{test_limit}] 正在穿透解析: {home_name} vs {away_name}")
        
        match_dict = {
            "match_id": event_id, "date": TODAY_STR,
            "tournament": event.get("tournament", {}).get("name"),
            "home_team": home_name, "away_team": away_name,
            "odds_data": {}, "h2h_data": {}, "lineups_data": {}
        }
        
        time.sleep(1.5)
        
        odds_res = fetch_via_proxy(f"{BASE_API}/event/{event_id}/odds/1/all", API_KEY)
        if odds_res: match_dict["odds_data"] = odds_res
            
        h2h_res = fetch_via_proxy(f"{BASE_API}/event/{event_id}/h2h", API_KEY)
        if h2h_res: match_dict["h2h_data"] = h2h_res
            
        lineups_res = fetch_via_proxy(f"{BASE_API}/event/{event_id}/lineups", API_KEY)
        if lineups_res: match_dict["lineups_data"] = lineups_res
            
        ai_dataset.append(match_dict)

    with open("ai_football_ready_data.json", "w", encoding="utf-8") as f:
        json.dump(ai_dataset, f, ensure_ascii=False, indent=4)
    print(f"🎯 终极数据集构建成功！")

if __name__ == "__main__":
    main()
