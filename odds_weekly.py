import os
import time
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

TG_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")

def send_tg(text):
    if not TG_TOKEN or not TG_CHAT_ID: return
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json={
            "chat_id": TG_CHAT_ID, "text": text[:4000], "parse_mode": "Markdown"
        }, timeout=30)
    except Exception as e:
        print(f"发送异常: {e}")

def main():
    t_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines_out = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled", "--no-sandbox"])
        page = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36").new_page()
        
        try:
            page.goto("https://www.pinnacle.com/en/soccer/matchups", timeout=45000, wait_until="domcontentloaded")
            time.sleep(6)
            
            # 1. 点击 LEAGUES
            page.evaluate("() => { const t = Array.from(document.querySelectorAll('button, div, span, a')).find(el => el.textContent.trim().toUpperCase() === 'LEAGUES'); if (t) t.click(); }")
            time.sleep(4)
            
            # 2. 点击英超
            success = page.evaluate("() => { const l = Array.from(document.querySelectorAll('a')); let t = l.find(el => el.textContent.includes('Premier League')); if (!t) t = Array.from(document.querySelectorAll('div, span, li')).find(el => el.textContent.trim() === 'England - Premier League'); if (t) { t.scrollIntoView(); t.dispatchEvent(new MouseEvent('click', {view: window, bubbles: true, cancelable: true, buttons: 1})); return true; } return false; }")
            if not success:
                page.locator("text=England - Premier League").first.click(force=True)
                
            time.sleep(8)
            
            # 3. 强力滚动内部容器：把页面上所有可能滚动的区块全部往下滚到底
            print("📜 正在强制滚动所有内部盘口容器...")
            page.evaluate("""() => {
                const scrollers = document.querySelectorAll('div');
                scrollers.forEach(el => {
                    if (el.scrollHeight > el.clientHeight) {
                        el.scrollTop = el.scrollHeight;
                    }
                });
                window.scrollTo(0, document.body.scrollHeight);
            }""")
            time.sleep(3)
            
            # 4. 提取纯文本并清洗
            body_text = page.evaluate("() => document.body.innerText")
            raw_lines = [l.strip() for l in body_text.split('\n') if l.strip()]
            
            start = False
            for l in raw_lines:
                if "England - Premier League" in l or "1X2" in l or "Spread" in l:
                    start = True
                if start:
                    if "About Pinnacle" in l or "Responsible Gaming" in l: break
                    lines_out.append(l)
                    
            if len(lines_out) < 5:
                lines_out = [l for l in raw_lines if not any(b in l for b in ["LOG IN", "JOIN", "SPORTS BETTING", "CASINO"])]
                
            # 放宽到 150 行，把后面的所有场次全部囊括进来
            lines_out = lines_out[:150]
        except Exception as e:
            print(f"异常: {e}")
        finally:
            browser.close()
            
    if lines_out:
        msg = f"🎯 *【Pinnacle 英超全量盘口】*\n🕒 `{t_str}`\n\n```text\n" + "\n".join(lines_out) + "\n```"
        send_tg(msg)
    else:
        send_tg(f"⚠️ *【监控提醒】* `{t_str}` 未能抓取到文字。")

if __name__ == "__main__":
    main()
