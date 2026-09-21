import os, time, requests
from datetime import datetime
from playwright.sync_api import sync_playwright

T, C = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")
def send(txt):
    if T and C:
        try: requests.post(f"https://api.telegram.org/bot{T}/sendMessage", json={"chat_id": C, "text": txt[:4000], "parse_mode": "Markdown"}, timeout=30); time.sleep(1)
        except: pass

def main():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    blocks, lines = [], []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=["--no-sandbox"])
        pg = b.new_context(viewport={"width": 1440, "height": 900}).new_page()
        try:
            pg.goto("https://www.pinnacle.com/en/soccer/matchups", timeout=45000)
            time.sleep(6)
            pg.evaluate("() => { const t = Array.from(document.querySelectorAll('button,div,span,a')).find(el => el.textContent.trim().toUpperCase() === 'LEAGUES'); if (t) t.click(); }")
            time.sleep(4)
            s = pg.evaluate("() => { const l = Array.from(document.querySelectorAll('a,div,span,li')).find(el => el.textContent.includes('Premier League')); if (l) { l.scrollIntoView(); l.click(); return true; } return false; }")
            if not s: pg.locator("text=England - Premier League").first.click(force=True)
            time.sleep(8)
            for _ in range(3):
                pg.evaluate("window.scrollBy(0, 800);")
                time.sleep(1.5)
            lines = [l.strip() for l in pg.evaluate("() => document.body.innerText").split('\n') if l.strip()]
        except: pass
        finally: b.close()
            
    parsed, i, start = [], 0, False
    for l in lines:
        if "England - Premier League" in l or "1X2" in l: start = True
        if start:
            if any(x in l for x in ["Choose Pinnacle", "TOP SPORTS", "BET SLIP", "About Pinnacle"]): break
            blocks.append(l)
            
    while i < len(blocks):
        if i + 1 < len(blocks) and "(Match)" in blocks[i] and "(Match)" in blocks[i+1]:
            h, a = blocks[i].replace(" (Match)", ""), blocks[i+1].replace(" (Match)", "")
            i += 2; mt, odds = "未定时", []
            while i < len(blocks):
                nxt = blocks[i]
                if "(Match)" in nxt or "SAT, " in nxt or "SUN, " in nxt or "MON, " in nxt: break
                if ":" in nxt and len(nxt) <= 5: mt = nxt
                else: odds.append(nxt)
                i += 1
            ml = [f"⚽ *{h} vs {a}* 🕒 `{mt}`"]
            if odds:
                to = [o for o in odds if o not in ["1", "X", "2", "HANDICAP", "OVER", "UNDER"] and not o.startswith("+")]
                if len(to) >= 3: ml.append(f"   🔹 `1X2` : " + " | ".join(to[:3]))
                if len(to) >= 7:
                    ml.append(f"   🔹 `亚盘` : " + " | ".join(to[3:7]))
                    ml.append(f"   🔹 `大小` : " + " | ".join(to[7:]))
            parsed.append("\n".join(ml))
        else: i += 1
        
    if parsed:
        mid = max(1, len(parsed) // 2)
        send(f"🎯 *【英超盘口 (上)】*\n🕒 `{ts}`\n\n" + "\n\n".join(parsed[:mid]))
        send(f"🎯 *【英超盘口 (下)】*\n🕒 `{ts}`\n\n" + "\n\n".join(parsed[mid:]))

if __name__ == "__main__": main()
