import os
import sys
import json
import requests
from datetime import datetime, timedelta, timezone

# 🎯 1. 严格对齐北京时间
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

    # 2. 抓取今日全球比赛大盘
    schedule_url = f"https://{API_HOST}/fixtures?date={TODAY_STR}"
    
    try:
        response = requests.get(schedule_url, headers=headers, timeout=15)
        if response.status_code != 200:
            sys.exit(1)
            
        fixtures = response.json().get("response", [])
        
        # 🎯 3. 【彻底修复的核心过滤器】：显式指定你想分析的顶级主流联赛 ID
        # 英超(39), 西甲(140), 意甲(135), 德甲(78), 法甲(61), 欧冠(2), 欧联(3)
        TARGET_LEAGUES = [39, 140, 135, 78, 61, 2, 3]
        
        # 强行过滤，只保留上述顶级联赛的比赛，把垃圾野鸡比赛全部扔掉！
        filtered_fixtures = [
            f for f in fixtures 
            if f.get("league", {}).get("id") in TARGET_LEAGUES
        ]
        
        # 💡 保底机制：如果恰逢五大联赛今天没有比赛，则精选今天全球最瞩目的前 3 场焦点战
        if not filtered_fixtures:
            print("💡 提示：今天暂无五大联赛赛程，自动切换为今日焦点国际/热门赛事...")
            filtered_fixtures = fixtures[:3]
            
        print(f"🎉 过滤成功！今日大盘共 {len(fixtures)} 场，已为你洗出 {len(filtered_fixtures)} 场高价值豪门大战。")
        
        ai_dataset = []
        
        # 限制只抓取精选出来的焦点豪门战，绝不超限，绝不抓垃圾
        for item in filtered_fixtures[:5]:
            fixture_id = item.get("fixture", {}).get("id")
            league_name = item.get("league", {}).get("name")
            home_name = item.get("teams", {}).get("home", {}).get("name")
            away_name = item.get("teams", {}).get("away", {}).get("name")
            
            match_dict = {
                "比赛ID": fixture_id,
                "联赛": league_name,
                "对阵": f"{home_name} VS {away_name}",
                "初盘即时赔率": {},
                "历史交锋简报": {},
                "首发伤停名单": {}
            }
            
            # 顺藤摸瓜拉取深度特征
            try:
                # 1. 赔率
                o_res = requests.get(f"https://{API_HOST}/odds?fixture={fixture_id}", headers=headers).json()
                match_dict["初盘即时赔率"] = o_res.get("response", [])[:1]
                
                # 2. H2H 历史交锋
                h_res = requests.get(f"https://{API_HOST}/fixtures/headtohead?h2h={item['teams']['home']['id']}-{item['teams']['away']['id']}", headers=headers).json()
                match_dict["历史交锋简报"] = h_res.get("response", [])[:5]
                
                # 3. 首发伤停
                l_res = requests.get(f"https://{API_HOST}/fixtures/lineups?fixture={fixture_id}", headers=headers).json()
                match_dict["首发伤停名单"] = l_res.get("response", [])
            except Exception:
                pass
                
            ai_dataset.append(match_dict)
            
        # 🎯 4. 直接把完美的、包含五大联赛豪门的特征 JSON 暴露出在日志中
        print("\n================== 🔥 AI 模型特供特征数据流 (直接复制下方文本) ==================")
        print(json.dumps(ai_dataset, ensure_ascii=False, indent=2))
        print("===============================================================================\n")
        
    except Exception as e:
        print(f"❌ 运行异常: {e}")

if __name__ == "__main__":
    main()
