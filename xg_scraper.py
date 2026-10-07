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
    except ImportError:
        print("请先安装 soccerdata")
        return

    seasons_to_try = ["2526", "2627", "2425"]
    rows = []
    used_season = None

    for season in seasons_to_try:
        print(f"尝试赛季: {season}")
        try:
            us = sd.Understat(leagues="ENG-Premier League", seasons=season)
            df = us.read_team_season_stats()
            print(f"  列名: {list(df.columns)}")
            print(f"  行数: {len(df)}")
            if len(df) == 0:
                continue

            cols = {str(c).lower(): c for c in df.columns}
            team_col = cols.get("team") or cols.get("title") or list(df.columns)[0]
            xg_col = cols.get("xg")
            xga_col = cols.get("xga")

            for _, r in df.iterrows():
                rows.append({
                    "联赛": "英超",
                    "赛季": season,
                    "球队": r.get(team_col, ""),
                    "xG": r.get(xg_col) if xg_col else None,
                    "xGA": r.get(xga_col) if xga_col else None,
                })
            used_season = season
            break
        except Exception as e:
            print(f"  失败: {e}")
            time.sleep(1)

    if not rows:
        print("没有抓到数据")
        return

    # 按 xG 排序
    rows.sort(key=lambda x: (x["xG"] or 0), reverse=True)

    wb = Workbook()
    ws = wb.active
    ws.title = "球队xG"
    ws.append(["联赛", "赛季", "球队", "xG", "xGA"])
    for r in rows:
        ws.append([r["联赛"], r["赛季"], r["球队"], r["xG"], r["xGA"]])

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    fname = f"xg_scraper_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    wb.save(fname)
    send_file(fname, caption=f"英超球队累计xG {ts}\n赛季 {used_season}\n共 {len(rows)} 队")
    print("已发送:", fname)

if __name__ == "__main__":
    main()
