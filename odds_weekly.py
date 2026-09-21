import os
import time
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

TG_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")

def send_telegram_photo(photo_path, caption):
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
    try:
        with open(photo_path, "rb") as photo:
            payload = {
                "chat_id": TG_CHAT_ID,
                "caption": caption,
                "parse_mode": "Markdown"
            }
            files = {"photo": photo}
            requests.post(url, data=payload, files=files, timeout=30)
    except Exception as e:
        print(f"发送异常: {e}")

def capture_pinnacle_direct_premier_league():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    screenshot_path = "pinnacle_epl_direct.png"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US"
        )
        
        page = context.new_page()
        
        try:
            # 1. 进入大盘主页
            target_url = "https://www.pinnacle.com/en/soccer/matchups"
            print(f"🌐 正在进入Pinnacle主页: {target_url}")
            page.goto(target_url, timeout=45000, wait_until="domcontentloaded")
            time.sleep(6)
            
            # 2. 点击 "LEAGUES" 标签
            print("📋 正在点击 LEAGUES...")
            clicked_leagues = page.evaluate("""() => {
                const tabs = Array.from(document.querySelectorAll('button, div, span, a'));
                const tab = tabs.find(el => el.textContent.trim().toUpperCase() === 'LEAGUES');
                if (tab) {
                    tab.click();
                    return true;
                }
                return false;
            }""")
            
            if not clicked_leagues:
                page.get_by_text("Leagues", exact=True).first.click()
                
            time.sleep(4)
            
            # 3. 直接点击列表里的 "England - Premier League"
            print("🎯 正在直接点击 England - Premier League...")
            clicked_epl = page.evaluate("""() => {
                const items = Array.from(document.querySelectorAll('div, span, a'));
                const epl = items.find(el => {
                    const text = el.textContent.trim();
                    return text.includes('England - Premier League');
                });
                if (epl) {
                    let clickable = epl.closest('a') || epl.closest('div[role="button"]') || epl;
                    clickable.click();
                    return true;
                }
                return false;
            }""")
            
            if not clicked_epl:
                page.get_by_text("England - Premier League", exact=False).first.click()
                
            time.sleep(6) # 等待英超赛程页面完全渲染
            print("✅ 成功直达英超赛程页面！")
            
            # 4. 截图保存
            page.screenshot(path=screenshot_path, full_page=False)
            print("📸 英超专区高清截图成功")
            
        except Exception as e:
            print(f"异常: {e}")
            page.screenshot(path=screenshot_path)
        finally:
            browser.close()
            
    caption = f"🎯 *【Pinnacle 英超盘口·极速直达】*\n🕒 时间: `{current_time}`\n🚀 状态: 首页 -> LEAGUES -> England - Premier League"
    if os.path.exists(screenshot_path):
        send_telegram_photo(screenshot_path, caption)

def main():
    capture_pinnacle_direct_premier_league()

if __name__ == "__main__":
    main()
