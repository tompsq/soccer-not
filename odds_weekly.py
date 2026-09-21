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

def capture_pinnacle_stable():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    screenshot_path = "pinnacle_fixed.png"
    
    with sync_playwright() as p:
        # 使用标准的桌面端浏览器，避免触发 H5 路由 404
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        
        # 增大分辨率并调整设备像素比 (device_scale_factor=2)，让截出来的字加倍清晰、放大！
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2, 
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US"
        )
        
        page = context.new_page()
        
        try:
            # 回到大盘根目录，确保 100% 成功加载
            target_url = "https://www.pinnacle.com/en/soccer/english-premier-league/matchups"
            print(f"🌐 正在访问大盘: {target_url}")
            
            page.goto(target_url, timeout=45000, wait_until="domcontentloaded")
            time.sleep(8) # 留足时间让赔率渲染
            
            # 尝试向下滚动一点，让英超核心板块完全展现在视口中央
            page.evaluate("window.scrollBy(0, 300)")
            time.sleep(2)
            
            # 截取当前高清视口
            page.screenshot(path=screenshot_path, full_page=False)
            print("📸 高清局部截图成功")
            
        except Exception as e:
            print(f"异常: {e}")
            page.screenshot(path=screenshot_path)
        finally:
            browser.close()
            
    caption = f"🎯 *【Pinnacle 盘口·高清局部监控】*\n🕒 时间: `{current_time}`\n🚀 状态: 桌面高清缩放渲染"
    if os.path.exists(screenshot_path):
        send_telegram_photo(screenshot_path, caption)

def main():
    capture_pinnacle_stable()

if __name__ == "__main__":
    main()
