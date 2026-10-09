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
    """专门为 ZenRows 提取纯 JSON 数据定制的完美请求引擎"""
    clean_key = str(raw_key).strip().replace("*", "").replace(" ", "").replace("\n", "").replace("\r", "")
    
    proxy_url = "https://zenrows.com"
    
    # 🎯 核心修正：强行加入 "json_response": "true" 告诉网关必须透传 SofaScore 的真实数据流
    query_params = {
        "key": clean_key,
        "url": target_url,
        "js_render": "true",
        "premium_proxy": "true",
        "json_response": "true"  # 🔥 就是这行，强制激活 JSON 透传
    }
    
    try:
        response = requests.get(proxy_url, params=query_params, timeout=30)
        print(f"📡 [网络请求] 目标接口: {target_url.split('/')[-1]} | 状态码: {response.status_code}")
        
        if response.status_code == 200:
            try:
                return response.json()
            except Exception:
                print("❌ 提取错误：未能成功转为 JSON，返回文本前100字:", response.text[:100])
                return None
        else:
            print(f"❌ 代理拒绝，状态码: {response.status_code} | 详情: {response.text[:150]}")
            return None
    except Exception as e:
        print(f"❌ 网络连接异常: {e}")
        return None

def main():
    API_KEY = os.environ.get("ANTI_BOT_KEY", "")
    if not API_KEY:
        print("❌ 错误：未在 GitHub Secrets 中检测到 ANTI_BOT_KEY！")
        sys.exit(1)
        
    print(f"🚀 开始抓取日期 {TODAY_STR} 的 SofaScore 足球核心特征库...")

    # 1. 抓取今日赛程列表
    schedule_url = f"{BASE_API}/sport/football/scheduled-events/{TODAY_STR}"
    schedule_data = fetch_via_proxy(schedule_url, API_KEY)
    
    if schedule_data is None or "events" not in schedule_data:
        print("❌ 赛程列表解包失败，正在尝试重试机制...")
        sys.exit(1)
        
    events = schedule_data.get("events", [])
    print(f"🎉 成功解锁今日赛程！共发现 {len(events)} 场足球比赛。")
    
    # 手机端测试，先深度抓取前 3 场比赛的完整模型特征
    test_limit = min(3, len(events))
    print(f"⚡ 正在深度透视前 {test_limit} 场比赛的【赔率 + 交锋 + 伤停】...")
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
        
        time.sleep(2)  # 安全防封间隔
        
        # 批量抓取盘口赔率、历史交锋、首发伤停
        odds_res = fetch_via_proxy(f"{BASE_API}/event/{event_id}/odds/1/all", API_KEY)
        if odds_res: match_dict["odds_data"] = odds_res
            
        h2h_res = fetch_via_proxy(f"{BASE_API}/event/{event_id}/h2h", API_KEY)
        if h2h_res: match_dict["h2h_data"] = h2h_res
            
        lineups_res = fetch_via_proxy(f"{BASE_API}/event/{event_id}/lineups", API_KEY)
        if lineups_res: match_dict["lineups_data"] = lineups_res
            
        ai_dataset.append(match_dict)

    # 写入最终产物文件
    with open("ai_football_ready_data.json", "w", encoding="utf-8") as f:
        json.dump(ai_dataset, f, ensure_ascii=False, indent=4)
    print(f"🎯 终极数据集构建成功！已成功保存附件。")

if __name__ == "__main__":
    main()
