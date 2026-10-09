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
    """超级容错请求函数：无论手机复制了什么杂质，都在这里强行洗净"""
    
    # 🧼 【核心修复】：强行将密钥转为字符串，并剔除所有星号、空格、换行符
    clean_key = str(raw_key).strip().replace("*", "").replace(" ", "").replace("\n", "").replace("\r", "")
    
    # 🎯 极其严格地拼装标准的 ZenRows 官方请求网关
    proxy_url = "https://zenrows.com"
    
    # 使用 requests 官方推荐的 params 字典传参，彻底避免字符串拼接导致的网址变形
    query_params = {
        "key": clean_key,
        "url": target_url,
        "js_render": "true",
        "premium_proxy": "true"
    }
    
    try:
        # 使用 params 传参，Python 会自动把 clean_key 安全地塞进 URL 中，绝不会再出现 zenrows.com*** 这样的致命错误！
        response = requests.get(proxy_url, params=query_params, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401 or response.status_code == 403:
            print(f"❌ 代理网关拒绝访问(状态码 {response.status_code})。说明洗干净后的 Key 依然不对，请确认您在 ZenRows 复制的是完整的 API Key，而不是带星号的预览图。")
            return None
        else:
            print(f"API 请求失败，状态码: {response.status_code}")
            return None
    except Exception as e:
        print(f"请求发生异常: {e}")
        return None

def main():
    # 1. 从 GitHub 变量中读取你的密钥
    API_KEY = os.environ.get("ANTI_BOT_KEY", "")
    if not API_KEY:
        print("❌ 错误：未在 GitHub Secrets 中检测到 ANTI_BOT_KEY！")
        sys.exit(1)
        
    print(f"🚀 开始抓取日期 {TODAY_STR} 的 SofaScore 足球核心特征库...")

    # 2. 抓取今日赛程列表
    schedule_url = f"{BASE_API}/sport/football/scheduled-events/{TODAY_STR}"
    schedule_data = fetch_via_proxy(schedule_url, API_KEY)
    
    if not schedule_data or "events" not in schedule_data:
        print("❌ 无法获取今日赛程列表。请检查你的 GitHub Secrets 里的密钥是否复制完整，或者 ZenRows 额度是否用完。")
        sys.exit(1)
        
    events = schedule_data.get("events", [])
    print(f"🎉 成功解锁今日赛程！共发现 {len(events)} 场足球比赛。")
    
    # 限制前 5 场核心比赛进行深度抓取，防止手机下载文件过大
    test_limit = min(5, len(events))
    print(f"⚡ 正在深度透视前 {test_limit} 场比赛的【赔率 + 交锋 + 伤停】数据...")
    
    ai_dataset = []

    for idx, event in enumerate(events[:test_limit]):
        event_id = event.get("id")
        home_name = event.get("homeTeam", {}).get("name")
        away_name = event.get("awayTeam", {}).get("name")
        print(f" ⏳ [{idx+1}/{test_limit}] 正在穿透解析: {home_name} vs {away_name}")
        
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
        
        time.sleep(1.5) # 缓冲间隔
        
        # 3. 抓取赔率 (Odds)
        odds_url = f"{BASE_API}/event/{event_id}/odds/1/all"
        odds_res = fetch_via_proxy(odds_url, API_KEY)
        if odds_res:
            match_dict["odds_data"] = odds_res
            
        # 4. 抓取历史交锋 (H2H)
        h2h_url = f"{BASE_API}/event/{event_id}/h2h"
        h2h_res = fetch_via_proxy(h2h_url, API_KEY)
        if h2h_res:
            match_dict["h2h_data"] = h2h_res
            
        # 5. 抓取首发阵型与伤停名单 (Lineups)
        lineups_url = f"{BASE_API}/event/{event_id}/lineups"
        lineups_res = fetch_via_proxy(lineups_url, API_KEY)
        if lineups_res:
            match_dict["lineups_data"] = lineups_res
            
        ai_dataset.append(match_dict)

    # 6. 保存数据
    output_filename = "ai_football_ready_data.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(ai_dataset, f, ensure_ascii=False, indent=4)
        
    print(f"🎯 终极数据集构建成功！已保存为: {output_filename}")

if __name__ == "__main__":
    main()
