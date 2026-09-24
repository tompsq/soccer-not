import os
import time
import requests
from datetime import datetime
from collections import defaultdict

T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")

# Premier League 固定 leagueId
LEAGUE_ID = 1980

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.pinnacle.com",
    "Referer": "https://www.pinnacle.com/",
}


def send(txt: str):
    if not T or not C:
        print(txt)
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{T}/sendMessage",
            json={"chat_id": C, "text": txt[:4000], "parse_mode": "Markdown"},
            timeout=30,
        )
        time.sleep(1)
    except Exception as e:
        print("TG send error:", e)


def american_to_decimal(american: int | float) -> float:
    """美式赔率转欧赔（保留3位小数）"""
    try:
        a = float(american)
        if a > 0:
            return round(a / 100 + 1, 3)
        else:
            return round(100 / abs(a) + 1, 3)
    except Exception:
        return 0.0


def get_json(url: str):
    for _ in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code == 200:
                return r.json()
        except Exception:
            time.sleep(1)
    return None


def main():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. 获取比赛列表
    matchups = get_json(f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{LEAGUE_ID}/matchups")
    if not matchups:
        send(f"⚠️ `{ts}` 无法获取 matchups 数据")
        return

    # 只保留常规比赛（type=matchup）
    matches = {}
    for m in matchups:
        if m.get("type") != "matchup":
            continue
        parts = m.get("participants", [])
        if len(parts) < 2:
            continue
        home = next((p["name"] for p in parts if p.get("alignment") == "home"), None)
        away = next((p["name"] for p in parts if p.get("alignment") == "away"), None)
        if not home or not away:
            continue
        start = m.get("startTime", "")[:16].replace("T", " ")  # 2026-10-10 14:00
        matches[m["id"]] = {
            "home": home,
            "away": away,
            "time": start,
            "1X2": {},
            "ah": None,          # (line, home_odds, away_odds)
            "ou": None,          # (line, over_odds, under_odds)
        }

    # 2. 获取盘口数据
    markets = get_json(f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{LEAGUE_ID}/markets/straight")
    if not markets:
        send(f"⚠️ `{ts}` 无法获取 markets 数据")
        return

    for mk in markets:
        mid = mk.get("matchupId")
        if mid not in matches:
            continue
        if mk.get("period") != 0:               # 只要全场
            continue
        if mk.get("isAlternate") is True:       # 只要主盘
            continue

        mtype = mk.get("type")
        prices = mk.get("prices", [])

        # ---------- 1X2 ----------
        if mtype == "moneyline":
            for p in prices:
                des = p.get("designation")
                if des in ("home", "draw", "away"):
                    matches[mid]["1X2"][des] = american_to_decimal(p["price"])

        # ---------- 亚盘 ----------
        elif mtype == "spread":
            # 主盘通常 isAlternate=false，取 points 最接近 0 的
            home_p = next((p for p in prices if p.get("designation") == "home"), None)
            away_p = next((p for p in prices if p.get("designation") == "away"), None)
            if home_p and away_p:
                line = home_p.get("points", 0)
                # 只保留主盘（|line| 较小的优先，这里简单取第一个主盘）
                if matches[mid]["ah"] is None or abs(line) < abs(matches[mid]["ah"][0]):
                    matches[mid]["ah"] = (
                        line,
                        american_to_decimal(home_p["price"]),
                        american_to_decimal(away_p["price"]),
                    )

        # ---------- 大小球 ----------
        elif mtype == "total":
            over_p = next((p for p in prices if p.get("designation") == "over"), None)
            under_p = next((p for p in prices if p.get("designation") == "under"), None)
            if over_p and under_p:
                line = over_p.get("points", 0)
                if matches[mid]["ou"] is None or abs(line - 2.5) < abs(matches[mid]["ou"][0] - 2.5):
                    # 优先取接近 2.5 的主盘
                    matches[mid]["ou"] = (
                        line,
                        american_to_decimal(over_p["price"]),
                        american_to_decimal(under_p["price"]),
                    )

    # 3. 组装消息
    final = []
    # 按开赛时间排序
    sorted_matches = sorted(matches.values(), key=lambda x: x["time"] or "9999")

    for m in sorted_matches:
        lines = [f"⚽ *{m['home']} vs {m['away']}* 🕒 `{m['time']}`"]

        # 1X2
        if len(m["1X2"]) >= 3:
            h = m["1X2"].get("home", "-")
            d = m["1X2"].get("draw", "-")
            a = m["1X2"].get("away", "-")
            lines.append(f"   🔹 `1X2` : {h} | {d} | {a}")

        # 亚盘
        if m["ah"]:
            line, h_odds, a_odds = m["ah"]
            # 显示习惯：主队盘口（负盘用-）
            line_str = f"{line:+g}" if line != 0 else "0"
            lines.append(f"   🔹 `亚盘` : 主{line_str} {h_odds} | 客 {a_odds}")

        # 大小球
        if m["ou"]:
            line, o_odds, u_odds = m["ou"]
            lines.append(f"   🔹 `大小` : {line} 大{o_odds} | 小{u_odds}")

        if len(lines) > 1:
            final.append("\n".join(lines))

    if not final:
        send(f"⚠️ `{ts}` 未解析出任何英超赛事盘口")
        return

    # 分上下两条发送，避免超长
    mid = max(1, len(final) // 2)
    send(f"🎯 *【Pinnacle 英超盘口 (上)】*\n🕒 `{ts}`\n\n" + "\n\n".join(final[:mid]))
    send(f"🎯 *【Pinnacle 英超盘口 (下)】*\n🕒 `{ts}`\n\n" + "\n\n".join(final[mid:]))


if __name__ == "__main__":
    main()   
