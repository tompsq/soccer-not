import os
import sys
import json
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

API_HOST = "v3.football.api-sports.io"

def main():
    API_KEY = os.environ.get("API_FOOTBALL_KEY", "")
    if not API_KEY:
        print("❌ 错误：未在 GitHub Secrets 中检测到密钥！")
        sys.exit(1)

    headers = {'x-rapidapi-host': API_HOST, 'x-rapidapi-key': API_KEY}
    
    # 🎯 【铁壁死锁过滤器】：39:英超, 140:西甲, 135:意甲, 78:德甲, 61:法甲
    # 不再盲目依赖当前日期查询，直接定点抽取五大联赛准备开踢的最新焦点战
    TARGET_LEAGUES = [39, 140, 135, 78, 61]
    
    fixtures = []
    print("🚀 正在强行检索顶级豪门（五大联赛）的最新核心赛程...")
    
    for league_id in TARGET_LEAGUES:
        # 获取该顶级联赛状态为“未开赛(NS)”或“最近准备开踢”的 2 场焦点战
        url = f"https://{API_HOST}/fixtures?league={league_id}&next=2"
        try:
            res = requests.get(url, headers=headers, timeout=15).json()
            fixtures.extend(res.get("response", []))
        except Exception as e:
            print(f"⚠️ 联赛 {league_id} 赛程拉取异常: {e}")

    if not fixtures:
        print("❌ 核心阻断：未能在官方库中检索到五大联赛的比赛。")
        sys.exit(1)

    print(f"🎉 成功绝杀野鸡！已精准为您锁定 {len(fixtures)} 场顶级豪门大战数据池。")
    
    sheet1_summary = []
    sheet2_xg_stats = []
    sheet3_h2h_details = []
    sheet4_injuries = []
    # 手机端运行为了绝对防止额度超限，每次精准深度解剖前 5 场最火爆的豪门硬仗
    for idx, item in enumerate(fixtures[:5]):
        fixture_id = item.get("fixture", {}).get("id")
        league_name = item.get("league", {}).get("name")
        match_date = item.get("fixture", {}).get("date", "")[:10]
        home_id = item['teams']['home']['id']
        away_id = item['teams']['away']['id']
        home_name = item['teams']['home']['name']
        away_name = item['teams']['away']['name']
        match_title = f"{home_name} VS {away_name}"
        
        print(f" ⏳ [{idx+1}/{min(5, len(fixtures))}] 正在深度剥离进阶特征: {match_title}")
        
        # ==================== 特征库 1：大盘与博彩初盘赔率 (Sheet 1) ====================
        o_url = f"https://{API_HOST}/odds?fixture={fixture_id}"
        home_win, draw_win, away_win = "", "", ""
        try:
            o_res = requests.get(o_url, headers=headers).json().get("response", [])
            if o_res:
                for bookmaker in o_res.get("bookmakers", []):
                    if bookmaker.get("name") in ["William Hill", "Bet365"]:
                        for bet in bookmaker.get("bets", []):
                            if bet.get("name") == "Match Winner":
                                for val in bet.get("values", []):
                                    if val.get("value") == "Home": home_win = val.get("odd")
                                    elif val.get("value") == "Draw": draw_win = val.get("odd")
                                    elif val.get("value") == "Away": away_win = val.get("odd")
                                break
        except Exception:
            pass
            
        sheet1_summary.append({
            "比赛ID": fixture_id, "联赛": league_name, "比赛日期": match_date, "对阵": match_title,
            "初盘-主胜": home_win, "初盘-平局": draw_win, "初盘-客胜": away_win
        })
        
        # ==================== 特征库 2：两队本赛季累计场均进球数统计 (Sheet 2) ====================
        stats_dict = {"对阵": match_title, "主队": home_name, "客队": away_name, "主队_场均进球": 0.0, "客队_场均进球": 0.0}
        try:
            h_stats_url = f"https://{API_HOST}/teams/statistics?season=2026&team={home_id}&league={item['league']['id']}"
            h_res = requests.get(h_stats_url, headers=headers).json().get("response", {})
            stats_dict["主队_场均进球"] = h_res.get("goals", {}).get("for", {}).get("average", {}).get("total", 0.0)
            
            a_stats_url = f"https://{API_HOST}/teams/statistics?season=2026&team={away_id}&league={item['league']['id']}"
            a_res = requests.get(a_stats_url, headers=headers).json().get("response", {})
            stats_dict["客队_场均进球"] = a_res.get("goals", {}).get("for", {}).get("average", {}).get("total", 0.0)
        except Exception:
            pass
        sheet2_xg_stats.append(stats_dict)
        
        # ==================== 特征库 3：历史交锋 H2H 具体详细赛果 (Sheet 3) ====================
        h_url = f"https://{API_HOST}/fixtures/headtohead?h2h={home_id}-{away_id}"
        try:
            h_res = requests.get(h_url, headers=headers).json().get("response", [])
            for h_match in h_res[:5]:
                hd = h_match.get("fixture", {}).get("date", "")[:10]
                hh = h_match.get("teams", {}).get("home", {}).get("name")
                ha = h_match.get("teams", {}).get("away", {}).get("name")
                h_goals_h = h_match.get("goals", {}).get("home")
                h_goals_a = h_match.get("goals", {}).get("away")
                sheet3_h2h_details.append({
                    "当前对阵": match_title, "历史交战日期": hd,
                    "历史主队": hh, "历史客队": ha,
                    "具体比分赛果": f"{h_goals_h}:{h_goals_a}"
                })
        except Exception:
            pass

        # ==================== 特征库 4：实时官宣两队伤停/红牌名单明细 (Sheet 4) ====================
        inj_url = f"https://{API_HOST}/injuries?fixture={fixture_id}"
        try:
            inj_res = requests.get(inj_url, headers=headers).json().get("response", [])
            if not inj_res:
                sheet4_injuries.append({
                    "对阵": match_title, "球队": "暂无官宣伤停/全员健康", "伤停人员": "无", "缺阵类型": "无", "缺阵原因": "无"
                })
            for inj_item in inj_res:
                sheet4_injuries.append({
                    "对阵": match_title,
                    "球队": inj_item.get("team", {}).get("name"),
                    "伤停人员": inj_item.get("player", {}).get("name"),
                    "缺阵类型": inj_item.get("player", {}).get("type", "伤病"),
                    "缺阵原因": inj_item.get("player", {}).get("reason", "未知")
                })
        except Exception:
            pass

    # ==================== 5. 使用 pandas 强行编译输出干净的 4-Sheet 大 Excel ====================
    output_filename = "Football_AI_Model_Data.xlsx"
    try:
        with pd.ExcelWriter(output_filename, engine="openpyxl") as writer:
            pd.DataFrame(sheet1_summary).to_excel(writer, sheet_name="1_五大联赛概要与赔率", index=False)
            pd.DataFrame(sheet2_xg_stats).to_excel(writer, sheet_name
