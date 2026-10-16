import asyncio
import aiohttp
import pandas as pd
from understat import Understat

async def main():
    # 定义需要抓取的五大联赛及其中文名称映射
    leagues_config = {
        "EPL": "英超",
        "La_liga": "西甲",
        "Serie_A": "意甲",
        "Bundesliga": "德甲",
        "Ligue_1": "法甲"
    }
    
    # 当前赛季年份（如 2026 代表 2026/2027 赛季）
    season_year = 2026 
    
    excel_filename = "understat_all_leagues_advanced.xlsx"
    
    async with aiohttp.ClientSession() as session:
        understat = Understat(session)
        
        # 使用 pandas ExcelWriter 将多个联赛写入同一个 Excel 的不同 Sheet
        with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
            for league_code, league_name in leagues_config.keys(), leagues_config.values():
                print(f"🔄 正在抓取 {league_name} ({league_code}) 高阶数据...")
                try:
                    raw_table = await understat.get_league_table(league_code, season_year)
                    
                    if not raw_table or len(raw_table) < 2:
                        print(f"⚠️ {league_name} 未获取到有效数据，跳过。")
                        continue
                        
                    headers = raw_table[0]
                    data_rows = raw_table[1:]
                    
                    parsed_list = []
                    for row in data_rows:
                        row_dict = dict(zip(headers, row))
                        
                        team_name = row_dict.get("Team", "")
                        matches = int(row_dict.get("M", 0))
                        pts = int(row_dict.get("PTS", 0))
                        xg = float(row_dict.get("xG", 0.0))
                        xga = float(row_dict.get("xGA", 0.0))
                        xpts = float(row_dict.get("xPTS", 0.0))
                        
                        parsed_list.append({
                            "球队": team_name,
                            "已赛场次": matches,
                            "实际积分": pts,
                            "预期积分(xPTS)": round(xpts, 2),
                            "总xG": round(xg, 2),
                            "场均xG": round(xg / matches, 2) if matches > 0 else 0,
                            "总xGA": round(xga, 2),
                            "场均xGA": round(xga / matches, 2) if matches > 0 else 0,
                            "xG净胜差": round(xg - xga, 2)
                        })
                        
                    df = pd.DataFrame(parsed_list)
                    # 按预期积分(xPTS)降序排列
                    df = df.sort_values(by="预期积分(xPTS)", ascending=False).reset_index(drop=True)
                    
                    # 写入对应的 Excel Sheet
                    df.to_excel(writer, sheet_name=league_name, index=False)
                    print(f"✅ {league_name} 抓取成功并已写入工作表！")
                    
                except Exception as e:
                    print(f"❌ 抓取 {league_name} 时发生错误: {e}")
                    
        print(f"\n🎉 所有联赛高阶数据已全部同步完成，并保存至 {excel_filename}！")

if __name__ == "__main__":
    asyncio.run(main())
