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
        print("❌ 错误：未检测到密钥！请检查 GitHub Secrets。")
        sys.exit(1)

    headers = {'x-rapidapi-host': API_HOST, 'x-rapidapi-key': API_KEY}
    
    # 🎯 2. 直接锁定今天的高价值主流联赛大盘（英超39, 西甲140, 意甲135, 德甲78, 法甲61, 欧冠2）
    # 我们直接用 URL 参数循环获取，彻底抛弃会留白的局部变量过滤器！
    target_leagues = [39, 140, 135, 78, 61, 2]
    fixtures = []
    
    print(f"🚀 开始通过官方网关提取北京时间 {TODAY_STR} 的五大联赛焦点赛程...")
    for league_id in target_leagues:
        url = f"https://{API_HOST}/fixtures?date={TODAY_STR}&league={league_id}"
        try:
            res = requests.get(url, headers=headers, timeout=15).json()
            fixtures.extend(res.get("response", []))
        except Exception as e:
            print(f"⚠️ 联赛 {league_id} 赛程拉取跳过: {e}")

    # 保底机制：如果今天恰逢五大联赛休赛，则直接拉取今天全球前 3 场瞩目大战
    if not fixtures:
        print("💡 提示：今日暂无五大联赛赛程，自动为你切换为今日全球焦点赛事...")
        try:
            backup_url = f"https://{API_HOST}/fixtures?date={TODAY_STR}"
            fixtures = requests.get(backup_url, headers=headers, timeout=15).json().get("response", [])[:3]
        except Exception:
            pass

    if not fixtures:
        print("❌ 核心阻断：今日全球范围内在 API 库中均未捕获到任何比赛。")
        sys.exit(1)

    print(f"🎉 赛程锁定成功！已为你提取到 {len(fixtures)} 场顶级高价值大战。")
    
    sheet1_summary = []
    sheet2_xg_stats = []
    sheet3_h2h_details = []
    sheet4_injuries = []

    # 手机端运行为了绝对防止额度超限，每次精准深度解剖前 3 场核心焦点大战
    for idx, item in enumerate(fixtures[:3]):
        fixture_id = item.get("fixture", {}).get("id")
        league_name = item.get("league", {}).get("name")
        home_id = item['teams']['home']['id']
        away_id = item['teams']['away']['id']
        home_name = item['teams']['home']['name']
        away_name = item['teams']['away']['name']
        match_title = f"{home_name} VS {away_name}"
        
        print(f" ⏳ [{idx+1}/3] 正在深度穿透挖掘特征: {match_title}")
        
        # ==================== 特征库 1：大盘与主流初盘赔率 (Sheet 1) ====================
        o_url = f"https://{API_HOST}/odds?fixture={fixture_id}"
        home_win, draw_win, away_win = "", "", ""
        try:
            o_res = requests.get(o_url, headers=headers).json().get("response", [])
            if o_res:
                for bookmaker in o_res[0].get("bookmakers", []):
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
            "比赛ID": fixture_id, "联赛": league_name, "对阵": match_title,
            "主流初盘-主胜": home_win, "主流初盘-平局": draw_win, "主流初盘-客胜": away_win
        })
        
        # ==================== 特征库 2：单场进阶 xG 预期进球 (Sheet 2) ====================
        s_url = f"https://{API_HOST}/fixtures/statistics?fixture={fixture_id}"
        stats_dict = {"对阵": match_title, "主队": home_name, "客队": away_name, "主队_xG": 0.0, "客队_xG": 0.0, "主队_射门": 0, "客队_射门": 0}
        try:
            s_res = requests.get(s_url, headers=headers).json().get("response", [])
            for s_item in s_res:
                t_name = s_item.get("team", {}).get("name")
                prefix = "主队_" if t_name == home_name else "客队_"
                for stat in s_item.get("statistics", []):
                    if stat.get("type") == "expected_goals" and stat.get("value"):
                        stats_dict[prefix + "xG"] = float(stat.get("value"))
                    elif stat.get("type") == "Total Shots" and stat.get("value"):
                        stats_dict[prefix + "射门"] = int(stat.get("value"))
        except Exception:
            pass
        sheet2_xg_stats.append(stats_dict)
        
        # ==================== 特征库 3：历史交锋 H2H 具体赛果 (Sheet 3) ====================
        h_url = f"https://{API_HOST}/fixtures/headtohead?h2h={home_id}-{away_id}"
        try:
            h_res = requests.get(h_url, headers=headers).json().get("response", [])
            for h_match in h_res[:6]: # 抓取最近 6 场历史真实比分
                h_date = h_match.get("fixture", {}).get("date", "")[:10]
                h_home = h_match.get("teams", {}).get("home", {}).get("name")
                h_away = h_match.get("teams", {}).get("away", {}).get("name")
                h_home_score = h_match.get("goals", {}).get("home")
                h_away_score = h_match.get("goals", {}).get("away")
                sheet3_h2h_details.append({
                    "当前对阵": match_title, "历史交战日期": h_date,
                    "历史主队": h_home, "历史客队": h_away,
                    "主队进球": h_home_score, "客队进球": h_away_score,
                    "具体赛果": f"{h_home_score}:{h_away_score}"
                })
        except Exception:
            pass

        # ==================== 特征库 4：实时官宣伤停名单明细 (Sheet 4) ====================
        # 官方开放网关专用的实时伤停与红牌缺阵库 (Injuries 接口)
        inj_url = f"https://{API_HOST}/injuries?fixture={fixture_id}"
        try:
            inj_res = requests.get(inj_url, headers=headers).json().get("response", [])
            if not inj_res:
                # 保底：如果本场比赛尚未录入伤停，输出教练与阵型战术特征作为 AI 模型替代输入
                sheet4_injuries.append({
                    "对阵": match_title, "球队": "全员健康/暂无官宣", "球员": "无", "类型": "无", "伤停原因": "无"
                })
            for inj_item in inj_res:
                sheet4_injuries.append({
                    "对阵": match_title,
                    "球队": inj_item.get("team", {}).get("name"),
                    "球员": inj_item.get("player", {}).get("name"),
                    "类型": inj_item.get("player", {}).get("type", "伤病"), # 区分红牌停赛还是伤病
                    "伤停原因": inj_item.get("player", {}).get("reason", "未知")
                })
        except Exception:
            pass

    # ==================== 5. 使用 pandas 强行编译输出双向平铺的 4-Sheet 大 Excel ====================
    try:
        output_filename = "Football_AI_Model_Data.xlsx"
        with pd.ExcelWriter(output_filename, engine="openpyxl") as writer:
            pd.DataFrame(sheet1_summary).to_excel(writer, sheet_name="1_核心赛程与赔率大盘", index=False)
            pd.DataFrame(sheet2_xg_stats).to_excel(writer, sheet_name="2_单场_xG_进阶统计", index=False)
            pd.DataFrame(sheet3_h2h_details).to_excel(writer, sheet_name="3_历史交锋_H2H_明细", index=False)
            pd.DataFrame(sheet4_injuries).to_excel(writer, sheet_name="4_两队官宣伤停明细", index=False)
        print(f"🎉 终极特征库 Excel 报表构建成功！文件名: {output_filename}")
    except Exception as e:
        print(f"❌ Excel 编译失败: {e}")

if __name__ == "__main__":
    main()
