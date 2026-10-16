import asyncio
import aiohttp
import pandas as pd
from understat import Understat

async def main():
    async with aiohttp.ClientSession() as session:
        understat = Understat(session)
        
        # 抓取 2024 赛季英超（EPL）所有球队的高阶统计数据
        # 包含：PPDA (压迫强度)、OPPDA (对手压迫强度)、xG、xGA、xPTS 等
        teams_data = await understat.get_league_teams("EPL", 2024)
        
        parsed_list = []
        for team in teams_data:
            t_name = team['title']
            history = team['history']
            
            # 汇总全季/近期的 PPDA 与 xG/xA
            total_ppda_att = sum(item['ppda']['att'] for item in history)
            total_ppda_def = sum(item['ppda']['def'] for item in history)
            ppda_val = round(total_ppda_att / total_ppda_def, 2) if total_ppda_def > 0 else 0
            
            total_xg = round(sum(item['xG'] for item in history), 2)
            total_xga = round(sum(item['xGA'] for item in history), 2)
            total_npxg = round(sum(item['npxG'] for item in history), 2)
            total_xpts = round(sum(item['xpts'] for item in history), 2)
            matches_played = len(history)
            
            parsed_list.append({
                "球队": t_name,
                "已赛场次": matches_played,
                "PPDA(压迫指数)": ppda_val,  # 数值越小，代表高位逼抢越凶猛
                "总xG": total_xg,
                "场均xG": round(total_xg / matches_played, 2),
                "总xGA": total_xga,
                "场均xGA": round(total_xga / matches_played, 2),
                "非点球xG": total_npxg,
                "预期积分(xPTS)": total_xpts
            })
            
        # 转换为 DataFrame 并按预期积分排序
        df = pd.DataFrame(parsed_list)
        df = df.sort_values(by="预期积分(xPTS)", ascending=False).reset_index(drop=True)
        
        print("=== Understat 抓取成功！数据预览 ===")
        print(df.to_string())
        
        # 导出为 Excel 档案
        df.to_excel("understat_epl_advanced.xlsx", index=False)
        print("\n✅ 数据已成功保存至 understat_epl_advanced.xlsx！")

if __name__ == "__main__":
    # 依赖库安装指令: pip install understat aiohttp pandas openpyxl
    asyncio.run(main())
