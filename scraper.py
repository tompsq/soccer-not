import os
import sys
import json
import requests
from datetime import datetime, timedelta, timezone

# 🎯 1. 严格锁定北京时间与当年赛季
SHA_TZ = timezone(timedelta(hours=8))
BEIJING_NOW = datetime.now(SHA_TZ)
TODAY_STR = BEIJING_NOW.strftime('%Y-%m-%d')

API_HOST = "v3.football.api-sports.io"

def main():
    API_KEY = os.environ.get("API_FOOTBALL_KEY", "")
    if not API_KEY:
        print("❌ 错误：未检测到密钥！")
        sys.exit(1)

    headers = {'x-rapidapi-host': API_HOST, 'x-rapidapi-key': API_KEY}

    # 2. 抓取大盘数据
    schedule_url = f"https://{API_HOST}/fixtures?date={TODAY_STR}"
    
    try:
        response = requests.get(schedule_url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"❌ 接口请求失败，状态码: {response.status_code}")
            sys.exit(1)
            
        fixtures = response.json().get("response", [])
        
        # 🎯 3. 【彻底修复的核心过滤器，坚决不再留白】：
        # 39: 英超, 140: 西甲, 135: 意甲, 78: 德甲, 61: 法甲, 2: 欧冠, 3: 欧联
        LEAGUE_FILTERS = [39, 140, 135, 78, 61, 2, 3]
        
        # 强制过滤，只保留五大联赛和欧冠
        filtered_fixtures = [
            f for f in fixtures 
            if f.get("league", {}).get("id") in LEAGUE_FILTERS
        ]
        
        # 💡 保底机制：如果今天恰逢五大联赛没有开打，则精选今天全球最瞩目的前 3 场热门焦点战
        if not filtered_fixtures:
            print("💡 提示：今日暂无五大联赛赛程，自动为你切换为今日精选热门国际/主流比赛...")
            filtered_fixtures = fixtures[:3]
            
        print(f"🎉 过滤器生效！今日大盘共 {len(fixtures)} 场，已为你彻底清洗过滤，只保留 {len(filtered_fixtures)} 场顶级大战。")
        
        ai_dataset = []
        
        # 手机端为了绝对防封超限，每次深度解剖前 3 场最具有分析价值的硬仗
        for item in filtered_fixtures[:3]:
            fixture_id = item.get("fixture", {}).get("id")
            league_name = item.get("league", {}).get("name")
            home_name = item.get("teams", {}).get("home", {}).get("name")
            away_name = item.get("teams", {}).get("away", {}).get("name")
            
            print(f" ⏳ 正在穿透抓取今日焦点特征 ({league_name}): {home_name} vs {away_name}")
            
            match_dict = {
                "比赛ID": fixture_id,
                "联赛": league_name,
                "对阵": f"{home_name} VS {away_name}",
                "初盘即时赔率": {},
                "历史交锋简报": {},
                "首发伤停名单": {},
                "单场进阶xG统计": {}  # 🎯 白嫖用户完全开放的 xG 特征字段
            }
            
            # 安全拉取子项特征数据
            try:
                # 实时赔率
                o_res = requests.get(f"https://{API_HOST}/odds?fixture={fixture_id}", headers=headers).json()
                match_dict["初盘即时赔率"] = o_res.get("response", [])[:1]
                
                # 近期交锋 (H2H)
                h_res = requests.get(f"https://{API_HOST}/fixtures/headtohead?h2h={item['teams']['home']['id']}-{item['teams']['away']['id']}", headers=headers).json()
                match_dict["历史交锋简报"] = h_res.get("response", [])[:5]
                
                # 官宣首发阵型
                l_res = requests.get(f"https://{API_HOST}/fixtures/lineups?fixture={fixture_id}", headers=headers).json()
                match_dict["首发伤停名单"] = l_res.get("response", [])
                
                # 🎯 抓取单场进阶技术统计（包含大模型最喜欢的 Expected Goals / xG）
                s_res = requests.get(f"https://{API_HOST}/fixtures/statistics?fixture={fixture_id}", headers=headers).json()
                match_dict["单场进阶xG统计"] = s_res.get("response", [])
            except Exception as inner_e:
                print(f" ⚠️ 部分子项抓取跳过: {inner_e}")
                
            ai_dataset.append(match_dict)
            
        # 🎯 4. 清洗出来的完美核心 JSON 直接打印在日志输出里，方便手机端直接长按复制
        print("\n================== 🔥 AI 模型特供特征数据流 (直接复制下方文本) ==================")
        print(json.dumps(ai_dataset, ensure_ascii=False, indent=2))
        print("===============================================================================\n")
        
        # 🎯 5. 同时本地保存一份，确保第5步的打包附件不会再报错报空！
        with open("ai_football_ready_data.json", "w", encoding="utf-8") as f:
            json.dump(ai_dataset, f, ensure_ascii=False, indent=4)
            
        print("🎯 本地数据文件 ai_football_ready_data.json 生成成功，准备上传附件。")
        
    except Exception as e:
        print(f"❌ 运行异常: {e}")

if __name__ == "__main__":
    main()
