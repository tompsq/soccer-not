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
    blocks = []

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
            # 先访问首页种 cookie，绕过 Cloudflare
            pg.goto("https://www.pinnacle.com/en/soccer/matchups",
                    timeout=60000, wait_until="domcontentloaded")
            time.sleep(8)

            body = pg.evaluate("() => document.body ? document.body.innerText : ''")
            if any(k in body for k in ["Just a moment", "Attention Required", "Checking your browser"]):
                send(f"⚠️ `{ts}` 被 Cloudflare 拦截，需要代理。")
                return

            # 进入 Leagues → England - Premier League
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

            # 滚动加载
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
            if not text_dump.strip():
                time.sleep(5)
                text_dump = pg.evaluate("() => document.body ? document.body.innerText : ''")

            lines = [l.strip() for l in text_dump.split("\n") if l.strip()]

            start = False
            for l in lines:
                if "England - Premier League" in l:
                    start = True
                    continue
                if start:
                    if any(k in l for k in ["About Pinnacle", "Responsible Gaming", "Choose Pinnacle"]):
                        break
                    if re.match(r'^\+\d+$', l):           # 过滤 +10
                        continue
                    if not re.search(r'\d+\.\d+', l) and " vs " not in l:
                        continue
                    blocks.append(l)

            # 调试兜底
            if not blocks and lines:
                preview = "\n".join(lines[:30])
                send(f"🔍 `{ts}` 页面有文字但未解析出比赛，前30行：\n```\n{preview[:1500]}\n```")

        except Exception as e:
            send(f"❌ `{ts}` 抓取异常: {str(e)[:200]}")
        finally:
            b.close()
          if not blocks:
        return

    # ===== 解析逻辑 =====
    parsed, i = [], 0
    while i < len(blocks):
        if " vs " in blocks[i] and len(blocks[i]) < 60 and not re.search(r'\d+\.\d+', blocks[i]):
            title = blocks[i]
            i += 1
            m_time, odds = "未定时", []
            while i < len(blocks):
                nxt = blocks[i]
                if " vs " in nxt and len(nxt) < 60 and not re.search(r'\d+\.\d+', nxt):
                    break
                if re.match(r'^\d{2}:\d{2}$', nxt):
                    m_time = nxt
                else:
                    odds.append(nxt)
                i += 1

            ml = [f"⚽ *{title}* 🕒 `{m_time}`"]
            if odds:
                to = [o for o in odds if re.search(r'\d+\.\d+', o)]
                if len(to) >= 3: ml.append(f"   🔹 `1X2` : " + " | ".join(to[:3]))
                if len(to) >= 7: ml.append(f"   🔹 `亚盘` : " + " | ".join(to[3:7]))
                if len(to) >= 9: ml.append(f"   🔹 `大小` : " + " | ".join(to[7:]))
                elif len(to) > 3: ml.append(f"   🔹 `盘口`: " + " | ".join(to[3:]))

            if len(ml) > 1:
                parsed.append("\n".join(ml))
        else:
            i += 1

    if parsed:
        mid = max(1, len(parsed) // 2)
        send(f"🎯 *【Pinnacle 英超盘口 (上)】*\n🕒 `{ts}`\n\n" + "\n\n".join(parsed[:mid]))
        send(f"🎯 *【Pinnacle 英超盘口 (下)】*\n🕒 `{ts}`\n\n" + "\n\n".join(parsed[mid:]))
    else:
        send(f"⚠️ `{ts}` 未解析到有效的赛事与赔率。")


if __name__ == "__main__":
    main()      
