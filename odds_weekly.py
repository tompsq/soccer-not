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
    matches = []

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled","--no-sandbox","--disable-dev-shm-usage","--disable-gpu"])
        ctx = b.new_context(viewport={"width": 1920, "height": 1080}, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", locale="en-US")
        ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
        pg = ctx.new_page()
        try:
            pg.goto("https://www.pinnacle.com/en/soccer/matchups", timeout=60000, wait_until="domcontentloaded")
            time.sleep(8)
            pg.evaluate("""() => { const t = Array.from(document.querySelectorAll('button,div,span,a')).find(el => el.textContent.trim().toUpperCase() === 'LEAGUES'); if (t) t.click(); }""")
            time.sleep(5)
            pg.evaluate("""() => { const t = Array.from(document.querySelectorAll('a,div,span,li')).find(el => el.textContent.trim() === 'England - Premier League'); if (t) { t.scrollIntoView(); t.click(); } }""")
            time.sleep(8)
            for _ in range(8):
                pg.evaluate("""() => { document.querySelectorAll('div').forEach(el => { if (el.scrollHeight > el.clientHeight) el.scrollTop += 600; }); window.scrollBy(0, 800); }""")
                time.sleep(1.5)
            time.sleep(4)

            # 🚨 核心改动：不使用 innerText，直接在 DOM 里按“场次”抓
            matches = pg.evaluate("""() => {
                const result = [];
                const allText = document.body.innerText;
                const lines = allText.split('\\n').map(l => l.trim()).filter(l => l);
                const matchRegex = /^\\(?Match\\)?$|^\\(?比赛\\)?$/;
                for (let i = 0; i < lines.length - 1; i++) {
                    const isHome = lines[i].includes('(Match)') || lines[i].includes('(比赛)');
                    const isAway = lines[i + 1].includes('(Match)') || lines[i + 1].includes('(比赛)');
                    if (isHome && isAway) {
                        const home = lines[i].replace('(Match)', '').replace('(比赛)', '').trim();
                        const away = lines[i + 1].replace('(Match)', '').replace('(比赛)', '').trim();
                        const start = i + 2;
                        const odds = [];
                        for (let j = start; j < Math.min(start + 20, lines.length); j++) {
                            if (lines[j].includes('(Match)') || lines[j].includes('(比赛)')) break;
                            if (/^\\d{2}:\\d{2}$/.test(lines[j])) continue;
                            if (/^[+-]?\\d+\\.\\d+$/.test(lines[j])) odds.push(lines[j]);
                            if (lines[j] === '+10' || lines[j] === '+5') { odds.push('+10'); break; }
                        }
                        if (odds.length > 0 && odds[odds.length - 1] === '+10') odds.pop();
                        if (odds.length >= 3) result.push({home, away, odds});
                    }
                }
                return result;
            }""")
        except Exception as e:
            send(f"❌ `{ts}` 抓取异常: {str(e)[:200]}")
        finally:
            b.close()

    if not matches:
        send(f"⚠️ `{ts}` 未抓到任何数据。")
        return

    parsed = []
    for m in matches:
        home, away, odds = m['home'], m['away'], m['odds']
        ml = [f"⚽ *{home} vs {away}*"]
        if len(odds) >= 3:
            ml.append(f"   🔹 `1X2` : {odds[0]} | {odds[1]} | {odds[2]}")
        if len(odds) >= 7:
            ml.append(f"   🔹 `亚盘` : 主{odds[3]} | 主{odds[4]} | 客 {odds[6]}")
        if len(odds) >= 11:
            ml.append(f"   🔹 `大小` : {odds[7]} | 大{odds[8]} | 小{odds[10]}")
        if len(ml) > 1:
            parsed.append("\n".join(ml))

    if parsed:
        mid = max(1, len(parsed) // 2)
        send(f"🎯 *【Pinnacle 英超盘口 (上)】*\n🕒 `{ts}`\n\n" + "\n\n".join(parsed[:mid]))
        send(f"🎯 *【Pinnacle 英超盘口 (下)】*\n🕒 `{ts}`\n\n" + "\n\n".join(parsed[mid:]))
    else:
        send(f"⚠️ `{ts}` 未解析出比赛。")

if __name__ == "__main__":
    main()
