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

def capture_pinnacle_mobile_h5():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    screenshot_path = "pinnacle_epl_mobile.png"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        
        # 核心改变：直接模拟手机设备环境 (iPhone 13/14 规格，开启移动端特征和触摸支持)
        iphone = p.devices["iPhone 13"]
        context = browser.new_context(
            **iphone,
            locale="en-US"
        )
        
        page = context.new_page()
        
        try:
            target_url = "https://www.pinnacle.com/en/soccer/matchups"
            print(f"🌐 正在以手机 H5 模式进入Pinnacle: {target_url}")
            page.goto(target_url, timeout=45000, wait_until="domcontentloaded")
            time.sleep(6)
            
            # 1. 在手机端点击菜单或 "LEAGUES" 标签
            print("📋 正在手机端寻找并点击联赛入口...")
            page.evaluate("""() => {
                const els = Array.from(document.querySelectorAll('button, div, span, a'));
                const target = els.find(el => el.textContent.trim().toUpperCase() === 'LEAGUES' || el.textContent.trim() === 'Soccer');
                if (target) target.click();
            }""")
            time.sleep(4)
            
            # 2. 点击英超联赛
            print("🎯 正在手机端点击 England - Premier League...")
            success = page.evaluate("""() => {
                const links = Array.from(document.querySelectorAll('a, div, span'));
                const target = links.find(el => el.textContent.includes('Premier League'));
                if (target) {
                    target.scrollIntoView();
                    target.click();
                    return true;
                }
                return false;
            }""")
            
            if not success:
                page.locator("text=Premier League").first.click(force=True)
                
            print("⏳ 等待手机端盘口渲染...")
            time.sleep(8)
            
            # 3. 手机端长截图：由于是 H5 布局，两边绝不会有宽屏大白边，字会自动撑满手机宽度
            page.screenshot(path=screenshot_path, full_page=True)
            print("📸 手机 H5 版长截图完成")
            
        except Exception as e:
            print(f"异常: {e}")
            page.screenshot(path=screenshot_path)
        finally:
            browser.close()
            
    caption = f"📱 *【Pinnacle 英超盘口·手机端纯净长图】*\n🕒 时间: `{current_time}`\n🚀 状态: 模拟移动端 H5 布局"
    if os.path.exists(screenshot_path):
        send_telegram_photo(screenshot_path, caption)

def main():
    capture_pinnacle_mobile_h5()

if __name__ == "__main__":
    main()
