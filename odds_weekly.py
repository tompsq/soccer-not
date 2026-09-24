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

    # ===== 临时调试：直接把原始文本前 60 行发给 TG =====
    if lines:
        preview = "\n".join(lines[:60])
        send(f"🔍 `{ts}` 原始页面前60行（调试用）：\n```\n{preview[:1800]}\n```")
    else:
        send(f"⚠️ `{ts}` 页面无文字。")

if __name__ == "__main__":
    main()
