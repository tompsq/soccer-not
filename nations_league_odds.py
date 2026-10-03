import os
import time
import json
import requests
from datetime import datetime, timedelta
from openpyxl import Workbook

# ================= 1. 配置与基础 API 请求模块 =================
API_KEY = os.getenv("ODDS_API_KEY", "你的API_KEY")
TG_TOKEN = os.getenv("TG_BOT_TOKEN", "你的TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID", "你的TG_CHAT_ID")

LEAGUES = [
    ("UEFA Nations League", "soccer_uefa_nations_league"),
]

def fetch(name, league_key, t_start, t_end):
    url = f"https://api.the-odds-api.com/v4/sports/{league_key}/odds/"
    params = {
        "apiKey": API_KEY,
        "regions": "eu,uk",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "decimal",
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code != 200:
            print(f"API请求失败 {name}: {r.status_code}, {r.text}")
            return []
        
        data = r.json()
        matches = []
        for item in data:
            ko_str = item.get("commence_time")
            if not ko_str:
                continue
            ko_dt = datetime.fromisoformat(ko_str.replace("Z", "+00:00"))
            ko_naive = ko_dt.replace(tzinfo=None) + timedelta(hours=8)
            
            if not (t_start <= ko_naive <= t_end):
                continue
                
            match_id = item.get("id")
            home = item.get("home_team")
            away = item.get("away_team")
            
            odds_1x2 = {}
            ah_data = []
            ou_data = []
            
            for bookmaker in item.get("bookmakers", []):
                if bookmaker.get("key") in ["pinnacle", "bet365"]:
                    for market in bookmaker.get("markets", []):
                        m_key = market.get("key")
                        if m_key == "h2h":
                            for out in market.get("outcomes", []):
                                name_team = out.get("name")
                                price = out.get("price")
                                if name_team == home:
                                    odds_1x2["home"] = price
                                elif name_team == away:
                                    odds_1x2["away"] = price
                                else:
                                    odds_1x2["draw"] = price
                        elif m_key == "spreads":
                            for out in market.get("outcomes", []):
                                if out.get("name") == home:
                                    ah_data = [market.get("last_update"), out.get("point"), out.get("price")]
                        elif m_key == "totals":
                            for out in market.get("outcomes", []):
                                if out.get("name") == "Over":
                                    ou_data = [market.get("last_update"), out.get("point"), out.get("price")]
                    if odds_1x2:
                        break
            
            matches.append({
                "id": match_id,
                "league": name,
                "home": home,
                "away": away,
                "kickoff": ko_naive.isoformat(),
                "time": ko_naive.strftime("%H:%M"),
                "1X2": odds_1x2,
                "ah": ah_data,
                "ou": ou_data
            })
        return matches
    except Exception as e:
        print(f"抓取异常 {name}: {e}")
        return []

def send(text):
    if not TG_TOKEN or not TG_CHAT_ID:
        print("未配置 Telegram 参数")
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"发送TG消息失败: {e}")

def send_file(filepath, caption=""):
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendDocument"
    try:
        with open(filepath, "rb") as f:
            files = {"document": f}
            data = {"chat_id": TG_CHAT_ID, "caption": caption, "parse_mode": "Markdown"}
            requests.post(url, data=data, files=files, timeout=30)
    except Exception as e:
        print(f"发送文件失败: {e}")
# ================= 2. 历史与缓存管理模块 =================
def load_history():
    if not os.path.exists("nations_history.json"):
        return {}
    try:
        with open("nations_history.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_history(history):
    try:
        with open("nations_history.json", "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存历史失败: {e}")

def load_xg_data():
    xg_file = "xg_data.json"
    if not os.path.exists(xg_file):
        default_xg = {
            "示例国家队": {"matches": 0, "xG_for": 0.0, "xG_against": 0.0}
        }
        try:
            with open(xg_file, "w", encoding="utf-8") as f:
                json.dump(default_xg, f, ensure_ascii=False, indent=2)
        except:
            pass
        return default_xg
    try:
        with open(xg_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def load_injuries_data():
    inj_file = "injuries_data.json"
    if not os.path.exists(inj_file):
        default_inj = {
            "示例国家队": {"missing_players": "无重大伤停", "impact": "低"}
        }
        try:
            with open(inj_file, "w", encoding="utf-8") as f:
                json.dump(default_inj, f, ensure_ascii=False, indent=2)
        except:
            pass
        return default_inj
    try:
        with open(inj_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}
# ================= 3. 主调度与 Excel 整合发送逻辑 =================
def main():
    now_my = datetime.utcnow() + timedelta(hours=8)
    tomorrow = now_my.date() + timedelta(days=1)
    t_start = datetime.combine(tomorrow, datetime.min.time())
    t_end = datetime.combine(tomorrow, datetime.max.time())
    ts = now_my.strftime("%Y-%m-%d %H:%M:%S")
    hour = now_my.hour

    print(f"当前大马时间：{ts}  小时={hour}")
    history = load_history()

    current_matches = []
    for name, lid in LEAGUES:
        rows = fetch(name, lid, t_start, t_end)
        print(f"{name}: {len(rows)} 场")
        current_matches.extend(rows)
        time.sleep(0.6)

    for m in current_matches:
        mid = m["id"]
        if mid not in history:
            history[mid] = {
                "league": m["league"],
                "home": m["home"],
                "away": m["away"],
                "time": m["time"],
                "kickoff": m["kickoff"],
                "open_1x2": m["1X2"],
                "open_ah": m["ah"],
                "open_ou": m["ou"],
                "curr_1x2": m["1X2"],
                "curr_ah": m["ah"],
                "curr_ou": m["ou"],
                "first_seen": ts,
                "last_seen": ts,
            }
        else:
            history[mid]["curr_1x2"] = m["1X2"]
            history[mid]["curr_ah"] = m["ah"]
            history[mid]["curr_ou"] = m["ou"]
            history[mid]["last_seen"] = ts
            history[mid]["time"] = m["time"]

    save_history(history)
    print(f"历史记录已更新，共 {len(history)} 场")

    if hour < 23:
        print("非最终运行，只更新历史，不发送")
        return

    rows = []
    for mid, h in history.items():
        try:
            ko = datetime.fromisoformat(h["kickoff"])
            if ko.date() != tomorrow:
                continue
        except:
            continue

        row = {
            "联赛": h["league"],
            "时间": h["time"],
            "主队": h["home"],
            "客队": h["away"],
            "开盘主胜": h["open_1x2"].get("home"),
            "开盘平局": h["open_1x2"].get("draw"),
            "开盘客胜": h["open_1x2"].get("away"),
            "临盘主胜": h["curr_1x2"].get("home"),
            "临盘平局": h["curr_1x2"].get("draw"),
            "临盘客胜": h["curr_1x2"].get("away"),
            "开盘亚盘": h["open_ah"][0] if h["open_ah"] else None,
            "开盘亚盘主": h["open_ah"][1] if h["open_ah"] else None,
            "开盘亚盘客": h["open_ah"][2] if h["open_ah"] else None,
            "临盘亚盘": h["curr_ah"][0] if h["curr_ah"] else None,
            "临盘亚盘主": h["curr_ah"][1] if h["curr_ah"] else None,
            "临盘亚盘客": h["curr_ah"][2] if h["curr_ah"] else None,
            "开盘大小": h["open_ou"][0] if h["open_ou"] else None,
            "开盘大": h["open_ou"][1] if h["open_ou"] else None,
            "开盘小": h["open_ou"][2] if h["open_ou"] else None,
            "临盘大小": h["curr_ou"][0] if h["curr_ou"] else None,
            "临盘大": h["curr_ou"][1] if h["curr_ou"] else None,
            "临盘小": h["curr_ou"][2] if h["curr_ou"] else None,
        }
        rows.append(row)

    if not rows:
        send(f"⚠️ `{ts}` 明天没有可发送的欧国联比赛")
        return

    # ================= 生成多 Sheet 综合 Excel =================
    wb = Workbook()
    
    # Sheet 1: 赔率开盘 vs 临盘
    ws1 = wb.active
    ws1.title = "开盘vs临盘"
    headers = list(rows[0].keys())
    ws1.append(headers)
    for r in rows:
        ws1.append([r.get(h) for h in headers])

    # Sheet 2: 球队 xG 数据缓存
    ws2 = wb.create_sheet(title="球队xG数据")
    ws2.append(["球队", "场次", "场均预期进球(xG)", "场均预期失球(xGA)"])
    xg_cache = load_xg_data()
    if xg_cache:
        for team, val in xg_cache.items():
            ws2.append([team, val.get("matches", 0), val.get("xG_for", 0), val.get("xG_against", 0)])

    # Sheet 3: 伤停情报缓存
    ws3 = wb.create_sheet(title="核心伤停情报")
    ws3.append(["球队", "关键伤停球员 / 停赛", "阵容影响评估"])
    inj_cache = load_injuries_data()
    if inj_cache:
        for team, val in inj_cache.items():
            ws3.append([team, val.get("missing_players", ""), val.get("impact", "")])

    fname = f"nations_open_close_{tomorrow.strftime('%Y%m%d')}.xlsx"
    wb.save(fname)

    # 推送 Telegram 文本摘要
    msg = f"📅 *【明天 ({tomorrow.strftime('%Y-%m-%d')}) 欧国联 综合情报】*\n🕒 `{ts}`\n共 {len(rows)} 场\n\n"
    for r in rows[:15]:
        msg += f"⚽ *{r['主队']} vs {r['客队']}* `{r['时间']}`\n"
        msg += f"   开盘 1X2: {r['开盘主胜']} | {r['开盘平局']} | {r['开盘客胜']}\n"
        msg += f"   临盘 1X2: {r['临盘主胜']} | {r['临盘平局']} | {r['临盘客胜']}\n\n"
    send(msg)

    # 推送包含 赔率 + xG + 伤停 的三合一 Excel 文件
    send_file(fname, caption=f"欧国联 赔率+xG+伤停 综合总表 {tomorrow.strftime('%Y-%m-%d')}（共{len(rows)}场）")
    print("最终报告已发送")

if __name__ == "__main__":
    main()
