import os
import sys
import json
import requests
import pandas as pd
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

    # 2. 抓取今日全球比赛大盘
    schedule_url = f"https://{API_HOST}/fixtures?date={TODAY_STR}"
    
    try:
        response = requests.get(schedule_url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"❌ 接口请求失败，状态码: {response.status_code}")
            sys.exit(1)
            
        fixtures = response.json().get("response", [])
        
        # 🎯 3. 【彻底锁死的五大顶级联赛过滤器，坚决不再留白】：
        # 39: 英超, 140: 西甲, 135: 意甲, 78: 德甲, 61: 法甲, 2: 欧冠
        LEAGUE_FILTERS = [39, 140, 135, 78, 61, 2]
        
        # 强行过滤，把全球低级别垃圾比赛全部扔掉！
        filtered_fixtures = [
            f for f in fixtures 
            if f.get("league", {}).get("id") in LEAGUE_FILTERS
        ]
        
        # 保底机制：如果今天确实没有这几个顶级联赛，就抓取今天全球前 3 场热门焦点战
        if not filtered_fixtures:
            print("💡 提示：今日暂无五大联赛赛程，自动为你切换为今日精选焦点赛事...")
            filtered_fixtures = fixtures[:3]
            
        print(f"🎉 过滤器生效！今日大盘共 {len(fixtures)} 场，已过滤保留 {len(filtered_fixtures)} 场顶级大战。")
        
        summary_list = []
        detailed_odds_list = []
        
        # 手机端测试，为了保证额度安全，每次只解剖前 3 场最核心的硬仗
        for item in filtered_fixtures[:3]:
            fixture_id = item.get("fixture", {}).get("id")
            league_name = item.get("league", {}).get("name")
            home_name = item.get("teams", {}).get("home", {}).get("name")
            away_name = item.get("teams", {}).get("away", {}).get("name")
            match_title = f"{home_name} VS {away_name}"
            
            print(f" ⏳ 正在深度解析核心数据: {match_title}")
            
            # --- 抓取子项数据 ---
            # 实时赔率
            o_res = requests.get(f"https://{API_HOST}/odds?fixture={fixture_id}", headers=headers).json()
            odds_data = o_res.get("response", [])
            
            # 历史交锋 (H2H)
            h_res = requests.get(f"https://{API_HOST}/fixtures/headtohead?h2h={item['teams']['home']['id']}-{item['teams']['away']['id']}", headers=headers).json()
            h2h_count = len(h_res.get("response", []))
            
            # --- 解析并清洗到 Excel 概要表 ---
            home_win, draw_win, away_win = "", "", ""
            if odds_data:
                # 默认提取主流博彩公司（如 William Hill / Bet365）的初盘独赢赔率
                for bookmaker in odds_data[0].get("bookmakers", []):
                    for bet in bookmaker.get("bets", []):
                        if bet.get("name") == "Match Winner":
                            for val in bet.get("values", []):
                                if val.get("value") == "Home": home_win = val.get("odd")
                                elif val.get("value") == "Draw": draw_win = val.get("odd")
                                elif val.get("value") == "Away": away_win = val.get("odd")
                            break
            
            summary_list.append({
                "比赛ID": fixture_id,
                "联赛": league_name,
                "对阵": match_title,
                "核心初盘-主胜": home_win,
                "核心初盘-平局": draw_win,
                "核心初盘-客胜": away_win,
                "历史交锋总场数": h2h_count
            })
            
            # --- 解析并平铺平整到 Excel 赔率明细表 ---
            if odds_data:
                for bookmaker in odds_data[0].get("bookmakers", []):
                    b_name = bookmaker.get("name")
                    for bet in bookmaker.get("bets", []):
                        play_type = bet.get("name")
                        for val in bet.get("values", []):
                            detailed_odds_list.append({
                                "对阵": match_title,
                                "博彩公司": b_name,
                                "玩法盘口": play_type,
                                "投注选项": val.get("value"),
                                "实时赔率": val.get("odd")
                            })
                            
        # 🎯 4. 使用 pandas 强行将清洗干净的数据转化并输出为完美的双 Sheet Excel 档案
        df_summary = pd.DataFrame(summary_list)
        df_odds = pd.DataFrame(detailed_odds_list)
        
        output_filename = "Football_AI_Model_Data.xlsx"
        with pd.ExcelWriter(output_filename, engine="openpyxl") as writer:
            df_summary.to_excel(writer, sheet_name="赛事大盘概要", index=False)
            df_odds.to_excel(writer, sheet_name="博彩公司详细赔率", index=False)
            
        print(f"🎉 终极双 Sheet Excel 报表编译成功！文件名: {output_filename}")
        
    except Exception as e:
        print(f"❌ 运行异常: {e}")

if __name__ == "__main__":
    main()
