import os
import sys
import json
import requests
from datetime import datetime

# 自动获取今天的日期 (格式: 2026-10-10)
TODAY_STR = datetime.today().strftime('%Y-%m-%d')
API_HOST = "v3.football.api-sports.io"

def main():
    # 读取你刚刚绑定的 API-Football 官方密钥
    API_KEY = os.environ.get("API_FOOTBALL_KEY", "")
    if not API_KEY:
        print("❌ 错误：未在 GitHub Secrets 中检测到密钥！")
        sys.exit(1)
        
    print(f"🚀 开始通过官方开放 API 抓取日期 {TODAY_STR} 的 AI 足球核心特征库...")

    # 官方标准请求头，直接通行
    headers = {
        'x-rapidapi-host': API_HOST,
        'x-rapidapi-key': API_KEY
    }

    # 1. 抓取今日赛程列表 (以英超联赛 League ID: 39 为例，你可以换成任意你想分析的联赛)
    # 英超 39, 西甲 140, 意甲 135, 欧冠 2
    schedule_url = f"https://{API_HOST}/fixtures?date={TODAY_STR}&league=39&season=2026"
    
    try:
        response = requests.get(schedule_url, headers=headers, timeout=15)
        print(f"📡 [官方数据网关] 状态码: {response.status_code}")
        
        if response.status_code != 200:
            print("❌ 密钥错误或今日无赛程")
            sys.exit(1)
            
        res_data = response.json()
        fixtures = res_data.get("response", [])
        print(f"🎉 成功！今日该联赛共发现 {len(fixtures)} 场足球赛事。")
        
        ai_dataset = []
        
        # 批量抓取前 3 场比赛的完整 AI 建模特征
        test_limit = min(3, len(fixtures))
        for idx, item in enumerate(fixtures[:test_limit]):
            fixture_id = item.get("fixture", {}).get("id")
            home_name = item.get("teams", {}).get("home", {}).get("name")
            away_name = item.get("teams", {}).get("away", {}).get("name")
            print(f" ⏳ [{idx+1}/{test_limit}] 正在获取官方特征数据: {home_name} vs {away_name}")
            
            match_dict = {
                "match_id": fixture_id,
                "date": TODAY_STR,
                "home_team": home_name,
                "away_team": away_name,
                "odds_data": {},
                "h2h_data": {},
                "lineups_data": {}
            }
            
            # 2. 获取本场比赛的盘口赔率 (Odds)
            odds_url = f"https://{API_HOST}/odds?fixture={fixture_id}"
            o_res = requests.get(odds_url, headers=headers).json()
            match_dict["odds_data"] = o_res.get("response", [])
            
            # 3. 获取两队历史交锋 (H2H)
            h2h_url = f"https://{API_HOST}/fixtures/headtohead?h2h={item['teams']['home']['id']}-{item['teams']['away']['id']}"
            h_res = requests.get(h2h_url, headers=headers).json()
            match_dict["h2h_data"] = h_res.get("response", [])
            
            # 4. 获取首发阵型与伤停名单 (Lineups)
            lineups_url = f"https://{API_HOST}/fixtures/lineups?fixture={fixture_id}"
            l_res = requests.get(lineups_url, headers=headers).json()
            match_dict["lineups_data"] = l_res.get("response", [])
            
            ai_dataset.append(match_dict)
            
        # 写入附件文件
        output_file = "ai_football_ready_data.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(ai_dataset, f, ensure_ascii=False, indent=4)
        print(f"🎯 官方终极特征包构建成功！已保存为 {output_file}")
        
    except Exception as e:
        print(f"❌ 运行异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
