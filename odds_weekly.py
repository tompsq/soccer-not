import os, time, requests
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
    blocks = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled", "--no-sandbox"])
        pg = b.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)").new_page()
        try:
            pg.goto("https://www.pinnacle.com/en/soccer/matchups", timeout=45000, wait_until="domcontentloaded")
            time.sleep(6)
            pg.evaluate("() => { const t = Array.from(document.querySelectorAll('button, div, span, a')).find(el => el.textContent.trim().toUpperCase() === 'LEAGUES'); if (t) t.click(); }")
            time.sleep(4)
            s = pg.evaluate("() => { const l = Array.from(document.querySelectorAll('a')); let t = l.find(el => el.textContent.includes('Premier League')); if (!t) t = Array.from(document.querySelectorAll('div, span, li')).find(el => el.textContent.trim() === 'England - Premier League'); if (t) { t.scrollIntoView(); t.dispatchEvent(new MouseEvent('click', {view: window, bubbles: true, cancelable: true, buttons: 1})); return true; } return false; }")
            if not s: pg.locator("text=England - Premier League").first.click(force=True)
            time.sleep(8)
            for _ in range(4):
                pg.evaluate("() => { document.querySelectorAll('div').forEach(el => { if (el.scrollHeight > el.clientHeight) el.scrollTop += 600; }); window.scrollBy(0, 800); }")
                time.sleep(1.5)
            time.sleep(3)
            lines = [l.strip() for l in pg.evaluate("() => document.body.innerText").split('\n') if l.strip()]
            start = False
            for l in lines:
                if "England - Premier League" in l or "1X2" in l: start = True
                if start:
                    if "About Pinnacle" in l or "Responsible Gaming" in l: break
                    blocks.append(l)
        except Exception as e: print(e)
        finally: b.close()
            
    if blocks:
        parsed, i = [], 0
        while i < len(blocks):
            if i + 1 < len(blocks) and "(Match)" in blocks[i] and "(Match)" in blocks[i+1]:
                home, away = blocks[i].replace(" (Match)", ""), blocks[i+1].replace(" (Match)", "")
                i += 2
                m_time, odds = "未定时", []
                while i < len(blocks):
                    nxt = blocks[i]
                    if "(Match)" in nxt or "SAT, " in nxt or "SUN, " in nxt or "MON, " in nxt: break
                    if ":" in nxt and len(nxt) <= 5: m_time = nxt
                    else: odds.append(nxt)
                    i += 1
                ml = [f"⚽ *{home} vs {away}* 🕒 `{m_time}`"]
                if odds:
                    to = [o for o in odds if o not in ["1", "X", "2", "HANDICAP", "OVER", "UNDER"]]
                    if len(to) >= 3: ml.append(f"   🔹 `1X2` : " + " | ".join(to[:3]))
                    if len(to) >= 7: ml.append(f"   🔹 `亚盘` : " + " | ".join(to[3:7]))
                    if len(to) >= 9: ml.append(f"   🔹 `大小` : " + " | ".join(to[7:]))
                    elif len(to) > 3: ml.append(f"   🔹 `盘口`: " + " | ".join(to[3:]))
                parsed.append("\n".join(ml))
            else: i += 1
        if parsed:
            mid = max(1, len(parsed) // 2)
            send(f"🎯 *【Pinnacle 英超盘口 (上)】*\n🕒 `{ts}`\n\n" + "\n\n".join(parsed[:mid]))
            send(f"🎯 *【Pinnacle 英超盘口 (下)】*\n🕒 `{ts}`\n\n" + "\n\n".join(parsed[mid:]))
        else: send(f"⚠️ `{ts}` 未解析到赛事。")
    else: send(f"⚠️ `{ts}` 未抓取到网页文字。")

if __name__ == "__main__": main()
