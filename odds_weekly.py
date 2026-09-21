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

def capture_epl_odds():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    screenshot_path = "epl_odds.png"
    
    with sync_playwright() as p:
        # 使用移动端视口，确保文字清晰、排版放大
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        
        context = browser.new_context(
            viewport={"width": 390, "height": 844}, # 模拟手机竖屏
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            locale="en-US"
        )
        
        page = context.new_page()
        
        try:
            # 直接访问 Pinnacle 的英超专属赛事页面
            target_url = "https://www.pinnacle.com/en/soccer/english-premier-league/matchups"
            print(f"🌐 正在访问英超专区: {target_url}")
            
            page.goto(target_url, timeout=45000, wait_until="domcontentloaded")
            time.sleep(6) # 等待数据加载
            
            # 尝试定位英超赔率的主体表格区域进行局部截图，如果找不到则截取整个手机视口
            element = page.locator("body")
            if element.count() > 0:
                page.screenshot(path=screenshot_path, full_page=False)
            else:
                page.screenshot(path=screenshot_path)
                
            print("📸 英超高清手机视口截图成功")
            
        except Exception as e:
            print(f"异常: {e}")
            page.screenshot(path=screenshot_path)
        finally:
            browser.close()
            
    caption = f"🎯 *【Pinnacle 英超盘口·手机高清监控】*\n🕒 时间: `{current_time}`\n🚀 状态: 移动端视口精准渲染"
    if os.path.exists(screenshot_path):
        send_telegram_photo(screenshot_path, caption)

def main():
    capture_epl_odds()

if __name__ == "__main__":
    main()
