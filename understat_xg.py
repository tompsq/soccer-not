import os, time, requests, re, json
from datetime import datetime
from openpyxl import Workbook

T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")

# Understat 联赛对应
LEAGUES = {
    "EPL": "英超",
    "La_liga": "西甲",
    "Serie_A": "意甲",
    "Bundesliga": "德甲",
}

H = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
}

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
        time.sleep(1)
    except Exception as e:
        print("发送失败:", e)

def get_understat_teams(league_key):
    """从 Understat 页面提取球队赛季 xG / xGA"""
    url = f"https://understat.com/league/{league_key}"
    try:
        r = requests.get(url, headers=H, timeout=20)
        if r.status_code != 200:
            print(f"{league_key} 状态码 {r.status_code}")
            return []
        # Understat 把数据放在 window.teamsData 里
        m = re.search(r"teamsData\s*=\s*JSON\.parse\('(.+?)'\)", r.text)
        if not m:
            print(f"{league_key} 未找到 teamsData")
            return []
        raw = m.group(1).encode().decode("unicode_escape")
        data = json.loads(raw)
        rows = []
        for tid, info in data.items():
            title = info.get("title", "")
            history = info.get("history", [])
            if not history:
                continue
            # 累计 xG / xGA
            xG = sum(float(h.get("xG", 0)) for h in history)
            xGA = sum(float(h.get("xGA", 0)) for h in history)
            matches = len(history)
            xG_avg = round(xG / matches, 3) if matches else 0
            xGA_avg = round(xGA / matches, 3) if matches else 0
            rows.append({
                "球队": title,
                "场次": matches,
                "总xG": round(xG, 2),
                "总xGA": round(xGA, 2),
                "场均xG": xG_avg,
                "场均xGA": xGA_avg,
            })
        # 按场均xG排序
        rows.sort(key=lambda x: x["场均xG"], reverse=True)
        return rows
    except Exception as e:
        print(f"{league_key} 错误: {e}")
        return []

def main():
    print("开始抓取 Understat 长期 xG...")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    all_data = []

    for key, name in LEAGUES.items():
        print(f"抓取 {name}...")
        teams = get_understat_teams(key)
        print(f"  → {len(teams)} 支球队")
        for t in teams:
            t["联赛"] = name
            all_data.append(t)
        time.sleep(1.5)

    if not all_data:
        print("没有抓到数据")
        return

    wb = Workbook()
    ws = wb.active
    ws.title = "长期xG"
    headers = ["联赛", "球队", "场次", "总xG", "总xGA", "场均xG", "场均xGA"]
    ws.append(headers)
    for r in all_data:
        ws.append([r.get(h) for h in headers])

    fname = f"understat_xg_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    wb.save(fname)
    send_file(fname, caption=f"Understat 长期xG {ts}\n共 {len(all_data)} 支球队")
    print("已发送:", fname)

if __name__ == "__main__":
    main()
