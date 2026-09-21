import os
import time
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

# === 第一部分：获取与清洗盘口 ===
def fetch_odds():
    print("🌐 启动浏览器抓取 Pinnacle 英超盘口...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(viewport={"width": 1440, "height": 900}, locale="en-US")
        page = context.new_page()
        try:
            page.goto("https://www.pinnacle.com/en/soccer/matchups", timeout=45000, wait_until="domcontentloaded")
            time.sleep(6)
            
            # 点击 LEAGUES
            page.evaluate("""() => {
                const tab = Array.from(p => p).find(el => el.textContent && el.textContent.trim().toUpperCase() === 'LEAGUES');
                // 简易点击
                const tabs = Array.from(document.querySelectorAll('button, div, span, a'));
                const t = tabs.find(el => el.textContent.trim().toUpperCase() === 'LEAGUES');
                if(t) t.click();
            }""")
            time.sleep(4)
            
            # 点击英超
            page.evaluate("""() => {
                const els = Array.from(document.querySelectorAll('div, span, a'));
                const epl = els.find(el => el.textContent.includes('England - Premier League'));
                if(epl) {
                    let btn = epl.closest('a') || epl.closest('div[role="button"]') || epl;
                    btn.click();
                }
            }""")
            time.sleep(8)
            
            # 提取文本
            body_text = page.evaluate("() => document.body.innerText")
            browser.close()
            
            # 清洗文本
            lines = [l.strip() for l in body_text.split('\n') if l.strip()]
            start, clean_lines = False, []
            for l in lines:
                if "England - Premier League Odds" in l: start = True
                if start:
                    if "About Pinnacle" in l: break
                    clean_lines.append(l)
            return clean_lines[:35] if clean_lines else lines[:30]
        except Exception as e:
            print(f"抓取异常: {e}")
            browser.close()
            return None

# === 第二部分：推送至 Telegram ===
def send_tg(lines):
    token, chat_id = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")
    if not token or not chat_id: return
    
    t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"🎯 *【Pinnacle 英超盘口】*\n🕒 `{t}`\n\n```text\n" + "\n".join(lines) + "\n```"
    
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
        "chat_id": chat_id, "text": msg, "parse_mode": "Markdown"
    })
    print("✅ 推送完成")

if __name__ == "__main__":
    data = fetch_odds()
    if data: send_tg(data)
