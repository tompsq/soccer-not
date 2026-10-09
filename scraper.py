import os
import sys
import json
import requests
from datetime import datetime, timedelta, timezone

# 🎯 核心修正：强行锁定东八区（北京时间），彻底解决 GitHub Actions 服务器时差问题
SHA_TZ = timezone(timedelta(hours=8))
# 自动获取当前北京时间的“年-月-日”以及当前年份
BEIJING_NOW = datetime.now(SHA_TZ)
TODAY_STR = BEIJING_NOW.strftime('%Y-%m-%d')
CURRENT_SEASON = str(BEIJING_NOW.year)

API_HOST = "v3.football.api-sports.io"

def main():
    API_KEY = os.environ.get("API_FOOTBALL_KEY", "")
    if not API_KEY:
        print("❌ 错误：未在 GitHub Secrets 中检测到 API_FOOTBALL_KEY！")
        sys.exit(1)
        
    print(f"🚀 已对齐北京时间！当前抓取日期: {TODAY_STR}，对应赛季: {CURRENT_SEASON}")

    headers = {
        'x-rapidapi-host': API_HOST,
        'x-rapidapi-key': API_KEY
    }

    # 🎯 黄金修正 2：不限联赛！直取北京时间今天全球所有正式比赛
    schedule_url = f"https://{API_HOST}/fixtures?date={TODAY_STR}"
    
    try:
        response = requests.get(schedule_url, headers=headers, timeout=15)
        print(f"📡 [官方数据网关] 状态码: {response.status_code}")
        
        if response.status_code != 200:
            print("❌ 密钥校验失败或服务器异常")
            sys.exit(1)
            
        res_data = response.json()
        fixtures = res_data.get("response", [])
        
        if not fixtures:
            print(f"⚠️ 今日 API 库中暂未发现比赛，请确认赛程安排。")
            sys.exit(0)
            
        print(f"🎉 成功！北京时间今天全球共发现 {len(fixtures)} 场赛事。")
        
        ai_dataset = []
        
        # 手机端测试，先深度抓取今天前 5 场热门比赛的【赔率 + 交锋 + 伤停】数据
        test_limit = min(5, len(fixtures))
        for idx, item in enumerate(fixtures[:test_limit]):
            fixture_id = item.get("fixture", {}).get("id")
            league_name = item.get("league", {}).get("name")
            home_name = item.get("teams", {}).get("home", {}).get("name")
            away_name = item.get("teams", {}).get("away", {}).get("name")
            
            print(f" ⏳ [{idx+1}/{test_limit}] 正在剥离特征 ({league_name}): {home_name} vs {away_name}")
            
            match_dict = {
                "match_id": fixture_id,
                "date": TODAY_STR,
                "league": league_name,
                "home_team": home_name,
                "away_team": away_name,
                "odds_data": {},
                "h2h_data": {},
                "lineups_data": {}
            }
            
            # 1. 抓取赔率 (Odds)
            odds_url = f"https://{API_HOST}/odds?fixture={fixture_id}"
            o_res = requests.get(odds_url, headers=headers).json()
            match_dict["odds_data"] = o_res.get("response", [])
            
            # 2. 抓取历史交锋 (H2H)
            h2h_url = f"https://{API_HOST}/fixtures/headtohead?h2h={item['teams']['home']['id']}-{item['teams']['away']['id']}"
            h_res = requests.get(h2h_url, headers=headers).json()
            match_dict["h2h_data"] = h_res.get("response", [])
            
            # 3. 抓取首发阵型与伤停名单 (Lineups)
            lineups_url = f"https://{API_HOST}/fixtures/lineups?fixture={fixture_id}"
            l_res = requests.get(lineups_url, headers=headers).json()
            match_dict["lineups_data"] = l_res.get("response", [])
            
            ai_dataset.append(match_dict)
            
        output_file = "ai_football_ready_data.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(ai_dataset, f, ensure_ascii=False, indent=4)
        print(f"🎯 终极模型特征包构建成功！已保存为 {output_file}")
        
    except Exception as e:
        print(f"❌ 运行异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
