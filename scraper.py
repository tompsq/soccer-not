import os
import sys
import json
import requests
import pandas as pd

API_HOST = "v3.football.api-sports.io"

def main():
    API_KEY = os.environ.get("API_FOOTBALL_KEY", "")
    if not API_KEY:
        print("❌ 错误：未检测到密钥！")
        sys.exit(1)

    headers = {'x-rapidapi-host': API_HOST, 'x-rapidapi-key': API_KEY}
    
    # 🎯 铁壁死锁五大联赛 ID：39:英超, 140:西甲, 135:意甲, 78:德甲, 61:法甲
    TARGET_LEAGUES = [39, 140, 135, 78, 61]
    fixtures = []
    
    print("🚀 正在检索五大联赛最新焦点赛程...")
    for league_id in TARGET_LEAGUES:
        url = f"https://{API_HOST}/fixtures?league={league_id}&next=2"
        try:
            res = requests.get(url, headers=headers, timeout=15).json()
            fixtures.extend(res.get("response", []))
        except Exception as e:
            print(f"⚠️ 联赛 {league_id} 异常: {e}")

    if not fixtures:
        print("❌ 未捕获到豪门赛程。")
        sys.exit(1)

    sheet1, sheet2, sheet3, sheet4 = [], [], [], []

    # 精准解剖前 5 场最火爆的豪门大战
    for item in fixtures[:5]:
        fixture_id = item.get("fixture", {}).get("id")
        league_name = item.get("league", {}).get("name")
        match_date = item.get("fixture", {}).get("date", "")[:10]
        home_id = item['teams']['home']['id']
        away_id = item['teams']['away']['id']
        home_name = item['teams']['home']['name']
        away_name = item['teams']['away']['name']
        match_title = f"{home_name} VS {away_name}"
        
        print(f" ⏳ 剥离进阶特征: {match_title}")
        
        # 1. 抓取初盘赔率
        h_win, d_win, a_win = "", "", ""
        try:
            o_res = requests.get(f"https://{API_HOST}/odds?fixture={fixture_id}", headers=headers).json().get("response", [])
            if o_res:
                for bm in o_res[0].get("bookmakers", []):
                    if bm.get("name") in ["William Hill", "Bet365"]:
                        for bet in bm.get("bets", []):
                            if bet.get("name") == "Match Winner":
                                for val in bet.get("values", []):
                                    if val.get("value") == "Home": h_win = val.get("odd")
                                    elif val.get("value") == "Draw": d_win = val.get("odd")
                                    elif val.get("value") == "Away": a_win = val.get("odd")
                                break
        except Exception:
            pass
            
        sheet1.append({
            "比赛ID": fixture_id, "联赛": league_name, "日期": match_date, "对阵": match_title,
            "初盘-主胜": h_win, "初盘-平局": d_win, "初盘-客胜": a_win
        })
        
        # 2. 抓取两队本赛季累计大样本进球率数据 (Sheet 2)
        stats_dict = {"对阵": match_title, "主队": home_name, "客队": away_name, "主队_场均进球": 0.0, "客队_场均进球": 0.0}
        try:
            h_res = requests.get(f"https://{API_HOST}/teams/statistics?season=2026&team={home_id}&league={item['league']['id']}", headers=headers).json().get("response", {})
            stats_dict["主队_场均进球"] = h_res.get("goals", {}).get("for", {}).get("average", {}).get("total", 0.0)
            a_res = requests.get(f"https://{API_HOST}/teams/statistics?season=2026&team={away_id}&league={item['league']['id']}", headers=headers).json().get("response", {})
            stats_dict["客队_场均进球"] = a_res.get("goals", {}).get("for", {}).get("average", {}).get("total", 0.0)
        except Exception:
            pass
        sheet2.append(stats_dict)
        
        # 3. 抓取两队 H2H 历史近期 5 场交手具体真实比分 (Sheet 3)
        try:
            h_res = requests.get(f"https://{API_HOST}/fixtures/headtohead?h2h={home_id}-{away_id}", headers=headers).json().get("response", [])
            for h_m in h_res[:5]:
                sheet3.append({
                    "当前对阵": match_title, "历史交战日期": h_m.get("fixture", {}).get("date", "")[:10],
                    "历史主队": h_m.get("teams", {}).get("home", {}).get("name"),
                    "历史客队": h_m.get("teams", {}).get("away", {}).get("name"),
                    "具体比分赛果": f"{h_m.get('goals', {}).get('home')}:{h_m.get('goals', {}).get('away')}"
                })
        except Exception:
            pass

        # 4. 抓取实时官宣伤停/红牌明细库 (Sheet 4)
        try:
            inj_res = requests.get(f"https://{API_HOST}/injuries?fixture={fixture_id}", headers=headers).json().get("response", [])
            if not inj_res:
                sheet4.append({"对阵": match_title, "球队": "暂无官宣伤停/全员健康", "伤停人员": "无", "缺阵类型": "无", "缺阵原因": "无"})
            for inj in inj_res:
                sheet4.append({
                    "对阵": match_title, "球队": inj.get("team", {}).get("name"),
                    "伤停人员": inj.get("player", {}).get("name"),
                    "缺阵类型": inj.get("player", {}).get("type", "伤病"),
                    "缺阵原因": inj.get("player", {}).get("reason", "未知")
                })
        except Exception:
            pass

    # ==================== 5. 使用 pandas 一体化安全编译输出 Excel ====================
    try:
        out_name = "Football_AI_Model_Data.xlsx"
        with pd.ExcelWriter(out_name, engine="openpyxl") as writer:
            pd.DataFrame(sheet1).to_excel(writer, sheet_name="1_五大联赛概要与赔率", index=False)
            pd.DataFrame(sheet2).to_excel(writer, sheet_name="2_大样本进阶场均统计", index=False)
            pd.DataFrame(sheet3).to_excel(writer, sheet_name="3_历史交锋H2H具体赛果", index=False)
            pd.DataFrame(sheet4).to_excel(writer, sheet_name="4_官方实战伤停名单明细", index=False)
        print(f"🎉 恭喜！终极纯净特征库 Excel 编译成功！")
    except Exception as e:
        print(f"❌ Excel 编译失败: {e}")

if __name__ == "__main__":
    main()
