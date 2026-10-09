import os
import sys
import json
import time
from datetime import datetime

# 自动获取今天的日期 (格式: 2026-10-10)
TODAY_STR = datetime.today().strftime('%Y-%m-%d')
BASE_API = "https://api.sofascore.com/api/v1"

def fetch_sofascore_data():
    # 🎯 核心绝杀 1：使用专门绕过高级反爬的 tls_client 库（需要在yml里安装）
    import tls_client
    
    # 模拟苹果手机 iPhone 15 的 Safari 浏览器底层安全指纹，彻底穿透 Cloudflare
    session = tls_client.Session(
        client_identifier="safari_ios_17", # 🔥 关键：注入苹果手机原生TLS指纹
        random_tls_extension_order=True
    )
    
    # 🎯 核心绝杀 2：完全伪造手机移动端微信/Safari 的请求头，让安全防火墙彻底信任
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Origin": "https://www.sofascore.com",
        "Referer": "https://www.sofascore.com/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "Connection": "keep-alive"
    }
    
    # 1. 先抓今日赛程列表
    schedule_url = f"{BASE_API}/sport/football/scheduled-events/{TODAY_STR}"
    print(f"🚀 正在以手机端指纹模式请求今日赛程...")
    
    try:
        response = session.get(schedule_url, headers=headers, timeout_seconds=15)
        print(f"📡 [网关回应] 状态码: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ 依然被拦截，状态码: {response.status_code}")
            return False
            
        schedule_data = response.json()
        events = schedule_data.get("events", [])
        print(f"🎉 绝杀成功！成功解锁赛程，今日共发现 {len(events)} 场足球比赛。")
        
        # 批量抓取前 3 场比赛的完整 AI 特征模型数据（赔率+交锋+首发）
        test_limit = min(3, len(events))
        print(f"⚡ 正在深度解析前 {test_limit} 场比赛的【赔率 + 交锋 + 伤停】数据...")
        ai_dataset = []
        
        for idx, event in enumerate(events[:test_limit]):
            event_id = event.get("id")
            home_name = event.get("homeTeam", {}).get("name")
            away_name = event.get("awayTeam", {}).get("name")
            print(f" ⏳ [{idx+1}/{test_limit}] 穿透分析中: {home_name} vs {away_name}")
            
            match_dict = {
                "match_id": event_id, "date": TODAY_STR,
                "tournament": event.get("tournament", {}).get("name"),
                "home_team": home_name, "away_team": away_name,
                "odds_data": {}, "h2h_data": {}, "lineups_data": {}
            }
            
            time.sleep(2) # 礼貌防封延迟
            
            # 抓取子项数据
            try:
                odds_res = session.get(f"{BASE_API}/event/{event_id}/odds/1/all", headers=headers)
                if odds_res.status_code == 200: match_dict["odds_data"] = odds_res.json()
                
                h2h_res = session.get(f"{BASE_API}/event/{event_id}/h2h", headers=headers)
                if h2h_res.status_code == 200: match_dict["h2h_data"] = h2h_res.json()
                
                lineups_res = session.get(f"{BASE_API}/event/{event_id}/lineups", headers=headers)
                if lineups_res.status_code == 200: match_dict["lineups_data"] = lineups_res.json()
            except Exception as inner_e:
                print(f" ⚠️ 某项子数据抓取微小跳过: {inner_e}")
                
            ai_dataset.append(match_dict)
            
        # 打包保存
        output_file = "ai_football_ready_data.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(ai_dataset, f, ensure_ascii=False, indent=4)
        print(f"🎯 终极特征包构建成功！已成功保存为 {output_file}")
        return True
        
    except Exception as e:
        print(f"❌ 发生未知异常: {e}")
        return False

if __name__ == "__main__":
    if not fetch_sofascore_data():
        sys.exit(1)
