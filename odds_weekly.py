import os
import time
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

def fetch_odds_and_screenshot():
    print("🌐 启动浏览器，恢复最稳健的直达与点击流程...")
    screenshot_path = "pinnacle_epl.png"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(
            viewport={"width": 1440, "height": 900}, 
            locale="en-US",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        try:
            # 回归最稳妥的直接访问方式（或者用之前验证过的可靠步骤）
            page.goto("https://www.pinnacle.com/en/soccer/matchups", timeout=45000, wait_until="domcontentloaded")
            print("⏳ 等待页面加载...")
            time.sleep(6)
            
            # 点击 LEAGUES
            print("📋 正在点击 LEAGUES...")
            page.evaluate("""() => {
                const tabs = Array.from(document.querySelectorAll('button, div, span, a'));
                const t = tabs.find(el => el.textContent && el.textContent.trim().toUpperCase() === 'LEAGUES');
                if(t) t.click();
            }""")
            time.sleep(4)
            
            # 点击英超
            print("🎯 正在点击英超...")
            page.evaluate("""() => {
                const els = Array.from(document.querySelectorAll('div, span, a'));
                const epl = els.find(el => el.textContent && el.textContent.includes('England - Premier League'));
                if(epl) {
                    let btn = epl.closest('a') || epl.closest('div[role="button"]') || epl;
                    btn.click();
                }
            }""")
            
            # 给予充足的渲染时间
            print("⏳ 等待英超盘口完全渲染...")
            time.sleep(12)
            
            # 截图留存
            print(f"📸 正在保存截图到 {screenshot_path}...")
            page.screenshot(path=screenshot_path, full_page=True)
            
            # 提取文本
            body_text = page.evaluate("() => document.body.innerText")
            browser.close()
            
            # 清洗文本
            lines = [l.strip() for l in body_text.split('\n') if l.strip()]
            
            clean_lines = []
            start_collect = False
            for l in lines:
                if "England - Premier League" in l or "SAT" in l or "SUN" in l or "1X2" in l:
                    start_collect = True
                
                if start_collect:
                    if "About Pinnacle" in l or "Responsible Gaming" in l:
                        break
                    clean_lines.append(l)
            
            if len(clean_lines) > 10:
                return screenshot_path, clean_lines[:40]
            else:
                blacklist = ["LOG IN", "JOIN", "SPORTS BETTING", "LIVE CENTRE", "CASINO", "Cookie", "ACCEPT", "Privacy"]
                filtered = [l for l in lines if not any(b in l for b in blacklist)]
                return screenshot_path, filtered[:40]
                
        except Exception as e:
            print(f"❌ 抓取异常: {e}")
            try: browser.close()
            except: pass
            return None, None

def send_to_telegram(screenshot_path, lines):
    token = os.environ.get("TG_BOT_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")
    if not token or not chat_id: return
    
    t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if screenshot_path and os.path.exists(screenshot_path):
        with open(screenshot_path, "rb") as photo:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendPhoto",
                data={"chat_id": chat_id, "caption": f"📸 *【网页截图】* - `{t}`", "parse_mode": "Markdown"},
                files={"photo": photo},
                timeout=30
            )
    
    if lines:
        msg = f"🎯 *【Pinnacle 英超盘口】*\n🕒 `{t}`\n\n```text\n" + "\n".join(lines) + "\n```"
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"},
            timeout=30
        )
    print("✅ 推送完成")

if __name__ == "__main__":
    img_path, data = fetch_odds_and_screenshot()
    if img_path or data:
        send_to_telegram(img_path, data)
