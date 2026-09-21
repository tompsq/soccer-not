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

def fmt(v):
    v = v.strip()
    return v[:-1] if re.match(r'^\d+\.\d{3}$', v) else v

def main():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    txt = ""
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
            txt = pg.evaluate("() => document.body.innerText")
        except Exception as e: print(e)
        finally: b.close()
            
    if txt:
        lines = [l.strip() for l in txt.split('\n') if l.strip()]
        parsed, i = [], 0
        while i < len(lines):
            if i + 1 < len(lines) and "(Match)" in lines[i] and "(Match)" in lines[i+1]:
                home, away = lines[i].replace(" (Match)", "").strip(), lines[i+1].replace(" (Match)", "").strip()
                i += 2
                pool, m_time = [], "未定时"
                while i < len(lines):
                    nxt = lines[i]
                    if "(Match)" in nxt or "About Pinnacle" in nxt: break
                    if ":" in nxt and len(nxt) <= 5 and not any(c.isalpha() for c in nxt): m_time = nxt
                    else: pool.append(nxt)
                    i += 1
                
                # 过滤掉 1, X, 2, 盘口名称，以及允许带+号的展开按钮（如 +10）但把它们从有效赔率/盘口中剔除
                to = [o for o in pool if o not in ["1", "X", "2", "HANDICAP", "OVER", "UNDER", "1X2"] and not o.startswith("+") and "LEAGUE" not in o.upper() and not re.match(r'^\+\d+$', o)]
                
                ml = [f"⚽ *{home} vs {away}* 🕒 `{m_time}`"]
                if len(to) >= 3:
                    ml.append(f"   🔹 `1X2` : " + " | ".join([fmt(x) for x in to[:3]]))
                    rem = [fmt(x) for x in to[3:]]
                    if len(rem) >= 4:
                        ml.append(f"   🔹 `亚盘` : {rem[0].ljust(4)} | {rem[1]} | {rem[2].ljust(4)} | {rem[3]}")
                        if len(rem) >= 8:
                            ml.append(f"   🔹 `大小` : {rem[4].ljust(4)} | {rem[5]} | {rem[6].ljust(4)} | {rem[7]}")
                        elif len(rem) >= 6:
                            ml.append(f"   🔹 `大小` : {rem[4].ljust(4)} | {rem[5]} | {rem[4].ljust(4)} | {rem[5]}")
                parsed.append("\n".join(ml))
            else: i += 1
            
        if parsed:
            mid = max(1, len(parsed) // 2)
            send(f"🎯 *【Pinnacle 英超盘口 (上)】*\n🕒 `{ts}`\n\n" + "\n\n".join(parsed[:mid]))
            send(f"🎯 *【Pinnacle 英超盘口 (下)】*\n🕒 `{ts}`\n\n" + "\n\n".join(parsed[mid:]))
        else: send(f"⚠️ `{ts}` 未解析到赛事。")
    else: send(f"⚠️ `{ts}` 未抓取到网页文本。")

if __name__ == "__main__": main()
