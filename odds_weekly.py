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

def capture_pinnacle_epl():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    screenshot_path = "pinnacle_epl.png"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2, # 双倍高清缩放
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US"
        )
        
        page = context.new_page()
        
        try:
            # 1. 访问 100% 成功的总大厅页面
            target_url = "https://www.pinnacle.com/en/soccer/matchups"
            print(f"🌐 正在连接大盘: {target_url}")
            page.goto(target_url, timeout=45000, wait_until="domcontentloaded")
            time.sleep(8) # 等待数据全部渲染
            
            # 2. 通过页面内嵌 JS 自动查找包含 "English Premier League" 或 "Premier League" 的元素并滚动到可视区域
            scrolled = page.evaluate("""() => {
                const elements = Array.from(document.querySelectorAll('*'));
                const eplElement = elements.find(el => el.textContent && el.textContent.includes('English Premier League') || el.textContent.includes('PREMIER LEAGUE'));
                if (eplElement) {
                    eplElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    return true;
                }
                return false;
            }""")
            
            if scrolled:
                print("🎯 已自动定位到英超板块")
                time.sleep(3) # 等待滚动后画面稳定
            else:
                print("⚠️ 未直接抓取到英超锚点，执行默认滚动")
                page.evaluate("window.scrollBy(0, 400)")
                time.sleep(2)
            
            # 3. 截取高清视口
            page.screenshot(path=screenshot_path, full_page=False)
            print("📸 英超局部高清截图成功")
            
        except Exception as e:
            print(f"异常: {e}")
            page.screenshot(path=screenshot_path)
        finally:
            browser.close()
            
    caption = f"🎯 *【Pinnacle 英超盘口·自动定位监控】*\n🕒 时间: `{current_time}`\n🚀 状态: 智能滚动与高清渲染"
    if os.path.exists(screenshot_path):
        send_telegram_photo(screenshot_path, caption)

def main():
    capture_pinnacle_epl()

if __name__ == "__main__":
    main()
