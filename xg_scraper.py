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
    print("开始用 soccerdata 抓 Understat 并汇总球队累计 xG...")
    try:
        import soccerdata as sd
        import pandas as pd
    except ImportError as e:
        print("缺少库:", e)
        return

    seasons_to_try = ["2526", "2627", "2425"]
    df = None
    used_season = None

    for season in seasons_to_try:
        print(f"尝试赛季: {season}")
        try:
            us = sd.Understat(leagues="ENG-Premier League", seasons=season)
            df = us.read_team_match_stats()
            print(f"  行数: {len(df)}")
            if df is not None and len(df) > 0:
                used_season = season
                break
        except Exception as e:
            print(f"  失败: {e}")
            time.sleep(1)

    if df is None or len(df) == 0:
        print("没有抓到数据")
        return

    # 汇总：每队作为主队的 xG + 作为客队的 xG
    team_xg = {}
    team_xga = {}
    team_matches = {}

    for _, r in df.iterrows():
        home = r.get("home_team")
        away = r.get("away_team")
        hxg = float(r.get("home_xg") or 0)
        axg = float(r.get("away_xg") or 0)

        for team, xg_for, xg_against in [
            (home, hxg, axg),
            (away, axg, hxg),
        ]:
            if not team:
                continue
            team_xg[team] = team_xg.get(team, 0) + xg_for
            team_xga[team] = team_xga.get(team, 0) + xg_against
            team_matches[team] = team_matches.get(team, 0) + 1

    rows = []
    for team in team_xg:
        n = team_matches[team]
        rows.append({
            "联赛": "英超",
            "赛季": used_season,
            "球队": team,
            "场次": n,
            "总xG": round(team_xg[team], 2),
            "总xGA": round(team_xga[team], 2),
            "场均xG": round(team_xg[team] / n, 3) if n else 0,
            "场均xGA": round(team_xga[team] / n, 3) if n else 0,
        })

    rows.sort(key=lambda x: x["总xG"], reverse=True)

    wb = Workbook()
    ws = wb.active
    ws.title = "球队累计xG"
    headers = ["联赛", "赛季", "球队", "场次", "总xG", "总xGA", "场均xG", "场均xGA"]
    ws.append(headers)
    for r in rows:
        ws.append([r[h] for h in headers])

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    fname = f"xg_scraper_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    wb.save(fname)
    send_file(fname, caption=f"英超球队累计xG {ts}\n赛季 {used_season}\n共 {len(rows)} 队")
    print("已发送:", fname)

if __name__ == "__main__":
    main()
