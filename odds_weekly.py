import os, time, requests, re
from datetime import datetime
from playwright.sync_api import sync_playwright

T, C = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")

def send(txt):
    if not T or not C: return
    try:
        requests.post(f"https://api.telegram.org/bot{T}/sendMessage",
                      json={"chat_id": C, "text": txt[:4000], "parse_mode": "Markdown"},
                      timeout=30)
        time.sleep(1)
    except Exception as e: print(e)

def main():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])
        ctx = b.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US")
        ctx.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
        pg = ctx.new_page()
        try:
            pg.goto("https://www.pinnacle.com/en/soccer/matchups",
                    timeout=60000, wait_until="domcontentloaded")
            time.sleep(8)
            pg.evaluate("""() => {
                const t = Array.from(document.querySelectorAll('button,div,span,a'))
                    .find(el => el.textContent.trim().toUpperCase() === 'LEAGUES');
                if (t) t.click();
            }""")
            time.sleep(5)
            pg.evaluate("""() => {
                const t = Array.from(document.querySelectorAll('a,div,span,li'))
                    .find(el => el.textContent.trim() === 'England - Premier League');
                if (t) { t.scrollIntoView(); t.click(); }
            }""")
            time.sleep(8)
            for _ in range(6):
                pg.evaluate("""() => {
                    document.querySelectorAll('div').forEach(el => {
                        if (el.scrollHeight > el.clientHeight) el.scrollTop += 600;
                    });
                    window.scrollBy(0, 800);
                }""")
                time.sleep(1.5)
            time.sleep(3)

            text_dump = pg.evaluate("() => document.body ? document.body.innerText : ''")
            lines = [l.strip() for l in text_dump.split("\n") if l.strip()]
        except Exception as e:
            send(f"❌ `{ts}` 抓取异常: {str(e)[:200]}")
        finally:
            b.close()
            # ===== 严格按照截图结构解析 =====
    if not lines:
        send(f"⚠️ `{ts}` 页面无文字。")
        return

    # 从第一场 "(Match)" 或 "(比赛)" 开始
    start_idx = next((i for i, l in enumerate(lines) if "(Match)" in l or "(比赛)" in l), -1)
    if start_idx == -1:
        send(f"⚠️ `{ts}` 未找到比赛标识，前30行：\n```\n" + "\n".join(lines[:30])[:1500] + "\n```")
        return

    data = lines[start_idx:]
    parsed, i = [], 0

    while i < len(data):
        if ("(Match)" in data[i] or "(比赛)" in data[i]) and i + 1 < len(data) and ("(Match)" in data[i+1] or "(比赛)" in data[i+1]):
            home = data[i].replace(" (Match)", "").replace(" (比赛)", "").strip()
            away = data[i + 1].replace(" (Match)", "").replace(" (比赛)", "").strip()
            i += 2
            m_time, odds = "未定时", []

            # 收集本场比赛的所有纯数字（忽略 +10）
            while i < len(data):
                nxt = data[i]
                if "(Match)" in nxt or "(比赛)" in nxt: break
                if re.match(r'^\d{2}:\d{2}$', nxt): m_time = nxt
                elif re.match(r'^[+-]?\d+\.\d+$', nxt): odds.append(nxt)
                i += 1

            ml = [f"⚽ *{home} vs {away}* 🕒 `{m_time}`"]

            # 按照截图真实结构严格切分
            if len(odds) >= 3:
                ml.append(f"   🔹 `1X2` : {odds[0]} | {odds[1]} | {odds[2]}")
            if len(odds) >= 7:
                ml.append(f"   🔹 `亚盘` : 主{odds[3]} | 主{odds[4]} | 客 {odds[6]}")
            if len(odds) >= 11:
                ml.append(f"   🔹 `大小` : {odds[7]} | 大{odds[8]} | 小{odds[10]}")

            if len(ml) > 1:
                parsed.append("\n".join(ml))
        else:
            i += 1

    if parsed:
        mid = max(1, len(parsed) // 2)
        send(f"🎯 *【Pinnacle 英超盘口 (上)】*\n🕒 `{ts}`\n\n" + "\n\n".join(parsed[:mid]))
        send(f"🎯 *【Pinnacle 英超盘口 (下)】*\n🕒 `{ts}`\n\n" + "\n\n".join(parsed[mid:]))
    else:
        send(f"⚠️ `{ts}` 未解析出比赛，前30行：\n```\n" + "\n".join(data[:30])[:1500] + "\n```")


if __name__ == "__main__":
    main()
