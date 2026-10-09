import os, requests
from datetime import datetime
from openpyxl import Workbook
from collections import Counter, defaultdict

T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")
KEY = os.environ.get("BIGBALLS_API_KEY")
BASE = "https://api.bigballsdata.com"

# 只保留需要抓取的联赛（已删除欧冠 + MLS）
LEAGUES = [
    ("EPL", "英超"),
    ("La Liga", "西甲"),
    ("Serie A", "意甲"),
    ("Bundesliga", "德甲"),
    ("Ligue 1", "法甲"),
]

# 英超已核对映射；其它联赛继续往里加即可
TEAM_MAP = {
    # ===== 英超（已核对）=====
    "bb_team_6xvcggo6fhj6": "Chelsea",
    "bb_team_6zmcfvtdqosl": "Sunderland",
    "bb_team_bku3akfbg5he": "Arsenal",
    "bb_team_bmnmmt2dqbek": "Aston Villa",
    "bb_team_e724gf4htpnl": "Brentford",
    "bb_team_efzvjqit6wuk": "Leicester",
    "bb_team_eoiz65w56j7g": "Tottenham",
    "bb_team_l6apkmfeheu6": "Brighton",
    "bb_team_o7j63lsrekzf": "Bournemouth",
    "bb_team_p6t3w2ul5sel": "Manchester United",
    "bb_team_y5cv6htoh5hu": "Fulham",
    "bb_team_y72vuylsqou7": "Fulham",

    # ===== 下面这些是你刚发的未知 ID，先占位，跑完后根据「未知team_id」表填真实队名 =====
    # 英超剩余
    # "bb_team_36zsft7lmkeu": "",
    # "bb_team_5rij6cmtyxsz": "",
    # "bb_team_cbw4c6xzwnfm": "",
    # "bb_team_rcstmd2lcg4t": "",
    # "bb_team_sgv2dwpvfeqx": "",
    # "bb_team_x7xjxfep527m": "",

    # 西甲 / 德甲 / 法甲 同理，跑一次后看「未知team_id」工作表（带样例球员），再回来补全即可
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
    except Exception as e:
        print("发送失败:", e)

def extract_items(data):
    if not data:
        return []
    block = data.get("data", data)
    if isinstance(block, dict):
        inj = block.get("injuries", block)
        if isinstance(inj, dict) and isinstance(inj.get("value"), list):
            return inj["value"]
        if isinstance(inj, list):
            return inj
    if isinstance(block, list):
        return block
    return []

def fetch_league(league_code):
    r = requests.get(
        f"{BASE}/v1/injuries?league={requests.utils.quote(league_code)}",
        headers={"Authorization": f"Bearer {KEY}", "Accept": "application/json"},
        timeout=20,
    )
    print(f"{league_code} -> {r.status_code}")
    if r.status_code != 200:
        print(r.text[:150])
        return []
    return extract_items(r.json())

def main():
    if not KEY:
        print("缺少 BIGBALLS_API_KEY")
        return

    all_rows = []
    # tid -> 样例球员名（方便后续映射）
    unknown_sample = {}

    for code, name in LEAGUES:
        items = fetch_league(code)
        print(f"  {name}: {len(items)} 人")
        for it in items:
            if not isinstance(it, dict):
                continue
            player = it.get("full_name") or it.get("display_name") or ""
            tid = it.get("current_team_id") or ""
            team = TEAM_MAP.get(tid, tid)
            if tid and tid not in TEAM_MAP:
                if tid not in unknown_sample and player:
                    unknown_sample[tid] = player
            all_rows.append({
                "联赛": name,
                "球队": team,
                "球员": player,
                "team_id": tid,
            })

    if not all_rows:
        print("没有任何数据")
        return

    all_rows.sort(key=lambda x: (x["联赛"], x["球队"], x["球员"]))

    wb = Workbook()
    ws = wb.active
    ws.title = "全部伤停"
    ws.append(["联赛", "球队", "球员"])
    for r in all_rows:
        ws.append([r["联赛"], r["球队"], r["球员"]])

    # 每个联赛一页汇总
    by_league = {}
    for r in all_rows:
        by_league.setdefault(r["联赛"], []).append(r)

    for league, rows in by_league.items():
        title = league[:28]
        ws_l = wb.create_sheet(title)
        ws_l.append(["球队", "人数", "球员"])
        by_team = {}
        for r in rows:
            by_team.setdefault(r["球队"], []).append(r["球员"])
        for team in sorted(by_team.keys()):
            ps = by_team[team]
            ws_l.append([team, len(ps), "、".join(ps)])

    # 未知 team_id 工作表（带样例球员，方便你映射）
    if unknown_sample:
        ws_u = wb.create_sheet("未知team_id")
        ws_u.append(["team_id", "出现次数", "样例球员", "建议队名（手动填）"])
        c = Counter(r["team_id"] for r in all_rows if r["team_id"] in unknown_sample)
        for tid, n in c.most_common():
            ws_u.append([tid, n, unknown_sample.get(tid, ""), ""])

    fname = f"injuries_multi_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    wb.save(fname)
    send_file(
        fname,
        caption=f"多联赛伤停名单\n共 {len(all_rows)} 人 / {len(by_league)} 联赛\n未知team_id: {len(unknown_sample)}",
    )
    print("未知 team_id 数量:", len(unknown_sample))
    print("已发送:", fname)

if __name__ == "__main__":
    main()
