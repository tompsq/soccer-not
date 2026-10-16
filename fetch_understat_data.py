import asyncio
import aiohttp
import pandas as pd
from understat import Understat

async def main():
    async with aiohttp.ClientSession() as session:
        understat = Understat(session)
        
        # 获取 2024 赛季英超 (EPL) 的积分与高阶数据表
        raw_table = await understat.get_league_table("EPL", 2026)
        
        if not raw_table or len(raw_table) < 2:
            print("❌ 未抓取到有效数据，请检查网络或赛季参数！")
            return
            
        # 第一行为表头，后续行为球队数据
        headers = raw_table[0]
        data_rows = raw_table[1:]
        
        parsed_list = []
        for row in data_rows:
            # 将表头与每行数据映射为字典
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
            
        # 转为 DataFrame 并按预期积分(xPTS)降序排列
        df = pd.DataFrame(parsed_list)
        df = df.sort_values(by="预期积分(xPTS)", ascending=False).reset_index(drop=True)
        
        print("\n=== Understat 英超高阶数据抓取成功 ===")
        print(df.to_string())
        
        # 导出保存为 Excel 文件
        excel_name = "understat_epl_advanced.xlsx"
        df.to_excel(excel_name, index=False)
        print(f"\n✅ 数据已成功保存至 {excel_name}！")

if __name__ == "__main__":
    # 依赖库: pip install understat aiohttp pandas openpyxl
    asyncio.run(main())
