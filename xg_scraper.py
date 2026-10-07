import os, time, requests
from datetime import datetime
from openpyxl import Workbook

T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")

def send_file(path, caption=""):
    if not T or not C:
        print("文件已生成:", path)
        return
    try:
        with open(path, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{T}/sendDocument",
                data={"chat_id": C, "caption": caption},
                files={"document": f},
                timeout=60,
            )
    except Exception as e:
        print("发送失败:", e)

def main():
    print("开始用 soccerdata 抓 Understat 球队累计 xG...")
    try:
        import soccerdata as sd
        import pandas as pd
    except ImportError as e:
        print("缺少库:", e)
        return

    seasons_to_try = ["2526", "2627", "2425"]
    rows = []
    used_season = None

    for season in seasons_to_try:
        print(f"尝试赛季: {season}")
        try:
            us = sd.Understat(leagues="ENG-Premier League", seasons=season)
            df = us.read_team_match_stats()
            print(f"  列名: {list(df.columns)}")
            print(f"  行数: {len(df)}")
            if df is None or len(df) == 0:
                continue

            # 打印前几列方便调试
            print(df.head(3))

            # 尝试按球队汇总 xG
            # 列名可能是 home_xg / away_xg 或类似
            cols = [c.lower() for c in df.columns]
            print("小写列名:", cols)

            # 简单汇总策略：找含 xg 的列和 team 相关列
            # 不同版本列名不同，先把整表存进 Excel 方便看
            for _, r in df.iterrows():
                rows.append({c: r.get(c) for c in df.columns})
            used_season = season
            break
        except Exception as e:
            print(f"  失败: {e}")
            time.sleep(1)

    if not rows:
        print("没有抓到数据")
        return

    wb = Workbook()
    ws = wb.active
    ws.title = "原始数据"
    headers = list(rows[0].keys())
    ws.append(headers)
    for r in rows:
        ws.append([r.get(h) for h in headers])

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    fname = f"xg_scraper_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    wb.save(fname)
    send_file(fname, caption=f"Understat 原始数据 {ts}\n赛季 {used_season}\n共 {len(rows)} 行")
    print("已发送:", fname)

if __name__ == "__main__":
    main()
