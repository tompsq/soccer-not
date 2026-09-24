import os, time, requests, re
from datetime import datetime
from playwright.sync_api import sync_playwright

T, C = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")

def send(txt):
    if not T or not C: return
    try:
        requests.post(f"https://api.telegram.org/bot{T}/sendMessage", json={"chat_id": C, "text": txt[:4000], "parse_mode": "Markdown"}, timeout=30)
        time.sleep(1)
    except Exception as e: print(e)

def main():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    captured = []

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])
        ctx = b.new_context(viewport={"width": 1920, "height": 1080}, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", locale="en-US")
        ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
        pg = ctx.new_page()

        # 🚨 核心：拦截网络请求
        def on_response(resp):
            url = resp.url
            if "arcadia.pinnacle.com" in url and ("matchups" in url or "odds" in url or "markets" in url):
                try:
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        captured.append(data)
                except Exception:
                    pass

        pg.on("response", on_response)

        try:
            pg.goto("https://www.pinnacle.com/en/soccer/matchups", timeout=60000, wait_until="domcontentloaded")
            time.sleep(10)
            pg.evaluate("""() => { const t = Array.from(document.querySelectorAll('button,div,span,a')).find(el => el.textContent.trim().toUpperCase() === 'LEAGUES'); if (t) t.click(); }""")
            time.sleep(5)
            pg.evaluate("""() => { const t = Array.from(document.querySelectorAll('a,div,span,li')).find(el => el.textContent.trim() === 'England - Premier League'); if (t) { t.scrollIntoView(); t.click(); } }""")
            time.sleep(15)  # 给 API 充足的响应时间

            # 滚动加载，触发更多比赛 API
            for _ in range(8):
                pg.evaluate("""() => { window.scrollBy(0, 800); }""")
                time.sleep(2)
            time.sleep(5)

        except Exception as e:
            send(f"❌ `{ts}` 抓取异常: {str(e)[:200]}")
        finally:
            b.close()

    if not captured:
        send(f"⚠️ `{ts}` 未捕获到 API 数据，请检查网络或页面结构。")
        return

    # ===== 解析 JSON 数据 =====
    parsed = {}
    for data in captured:
        for item in data:
            if not isinstance(item, dict): continue
            # 抓取比赛名称和时间
            home = away = None
            if "home" in item and "away" in item:
                home = item.get("home", "")
                away = item.get("away", "")
            elif "participants" in item:
                parts = item["participants"]
                if len(parts) >= 2:
                    home, away = parts[0].get("name"), parts[1].get("name")
            if not home or not away: continue

            match_id = str(item.get("id", ""))
            if match_id not in parsed:
                parsed[match_id] = {"home": home, "away": away, "1X2": [], "亚盘": [], "大小": []}

            # 遍历市场数据
            markets = item.get("markets", [])
            for mk in markets:
                mk_type = mk.get("type", "")
                prices = mk.get("prices", [])
                if mk_type == "moneyline":
                    parsed[match_id]["1X2"] = [p.get("price") for p in prices if "price" in p]
                elif mk_type == "spread":
                    parsed[match_id]["亚盘"] = [p.get("price") for p in prices if "price" in p]
                elif mk_type == "total":
                    parsed[match_id]["大小"] = [p.get("price") for p in prices if "price" in p]

    # ===== 组装消息 =====
    final_msgs = []
    for mid, m in parsed.items():
        ml = [f"⚽ *{m['home']} vs {m['away']}*"]
        if len(m["1X2"]) >= 3:
            ml.append(f"   🔹 `1X2` : {m['1X2'][0]} | {m['1X2'][1]} | {m['1X2'][2]}")
        if len(m["亚盘"]) >= 3:
            ml.append(f"   🔹 `亚盘` : 主{m['亚盘'][0]} | 客 {m['亚盘'][1]}")
        if len(m["大小"]) >= 2:
            ml.append(f"   🔹 `大小` : 大{m['大小'][0]} | 小{m['大小'][1]}")
        if len(ml) > 1:
            final_msgs.append("\n".join(ml))

    if final_msgs:
        mid = max(1, len(final_msgs) // 2)
        send(f"🎯 *【Pinnacle 英超盘口 (上)】*\n🕒 `{ts}`\n\n" + "\n\n".join(final_msgs[:mid]))
        send(f"🎯 *【Pinnacle 英超盘口 (下)】*\n🕒 `{ts}`\n\n" + "\n\n".join(final_msgs[mid:]))
    else:
        send(f"⚠️ `{ts}` 解析失败，未能组装出任何比赛消息。")

if __name__ == "__main__":
    main()
