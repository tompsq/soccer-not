import os, time, requests
from datetime import datetime
from playwright.sync_api import sync_playwright

T, C = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")
def send(txt):
    if T and C:
        try: requests.post(f"https://api.telegram.org/bot{T}/sendMessage", json={"chat_id": C, "text": txt[:4000], "parse_mode": "Markdown"}, timeout=30); time.sleep(1)
        except Exception as e: print(e)

def main():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bks = []
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled", "--no-sandbox"])
        pg = br.new_context(viewport={"width": 1440, "height": 900}, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)").new_page()
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
            st = False
            for l in lines:
                if "England - Premier League" in l or "1X2" in l: st = True
                if st:
                    if "About Pinnacle" in l or "Responsible Gaming" in l: break
                    bks.append(l)
        except Exception as e: print(e)
        finally: br.close()
            
    if bks:
        parsed, i = [], 0
        while i < len(bks):
            if i + 1 < len(bks) and "(Match)" in bks[i] and "(Match)" in bks[i+1]:
                h, a = bks[i].replace(" (Match)", ""), bks[i+1].replace(" (Match)", "")
                i += 2
                mt, odds = "未定时", []
                while i < len(bks):
                    nxt = bks[i]
                    if "(Match)" in nxt or "SAT, " in nxt or "SUN, " in nxt or "MON, " in nxt: break
                    if ":" in nxt and len(nxt) <= 5: mt = nxt
                    else: odds.append(nxt)
                    i += 1
                ml = [f"⚽ *{h} vs {a}* 🕒 `{mt}`"]
                if odds:
                    to = [o for o in odds if o not in ["1", "X", "2", "HANDICAP", "OVER", "UNDER"] and not o.startswith("+")]
                    if len(to) >= 3: ml.append(f"   🔹 `1X2` : " + " | ".join(to[:3]))
                    if len(to) >= 7: ml.append(f"   🔹 `亚盘` : " + " | ".join(to[3:7]))
                    if len(to) >= 10: ml.append(f"   🔹 `大小` : 大小：{to[7]} | 大 {to[8]} | 小 {to[9]}")
                parsed.append("\n".join(ml))
            else: i += 1
        if parsed:
            mid = max(1, len(parsed) // 2)
            send(f"🎯 *【Pinnacle 英超盘口 (上)】*\n🕒 `{ts}`\n\n" + "\n\n".join(parsed[:mid]))
            send(f"🎯 *【Pinnacle 英超盘口 (下)】*\n🕒 `{ts}`\n\n" + "\n\n".join(parsed[mid:]))
        else: send(f"⚠️ `{ts}` 未解析到赛事。")
    else: send(f"⚠️ `{ts}` 未抓取到文字。")

if __name__ == "__main__": main()
