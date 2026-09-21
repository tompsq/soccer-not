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

def capture_pinnacle_epl_exact():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    screenshot_path = "pinnacle_epl_exact.png"
    
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
            target_url = "https://www.pinnacle.com/en/soccer/matchups"
            print(f"🌐 正在连接大盘: {target_url}")
            page.goto(target_url, timeout=45000, wait_until="domcontentloaded")
            time.sleep(8) # 等待数据完全加载
            
            # 使用更严谨的 JS 查找英超联赛标题，并把整个联赛区块滚动到屏幕正中心
            epl_found = page.evaluate("""() => {
                const headers = Array.from(document.querySelectorAll('div, span, h2, h3'));
                // 寻找包含 PREMIER LEAGUE 且带有英文前缀的专区标题
                const target = headers.find(el => {
                    const text = el.textContent.trim().toUpperCase();
                    return text.includes('ENGLISH PREMIER LEAGUE') || (text.includes('PREMIER LEAGUE') && !text.includes('U21') && !text.includes('WOMEN'));
                });
                
                if (target) {
                    // 向上追溯到包含该联赛所有比赛赔率的父容器卡片
                    let container = target.closest('div[class*="style__Container"]') || target.parentElement.parentElement.parentElement;
                    if (container) {
                        container.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        return true;
                    }
                }
                return false;
            }""")
            
            if epl_found:
                print("🎯 成功精准定位到英超板块并滚动")
                time.sleep(3)
            else:
                print("⚠️ 未能精准匹配英超容器，执行备用滚动方案")
                page.evaluate("window.scrollBy(0, 600)")
                time.sleep(2)
            
            # 截取当前高质量视口
            page.screenshot(path=screenshot_path, full_page=False)
            print("📸 英超板块高清截图成功")
            
        except Exception as e:
            print(f"异常: {e}")
            page.screenshot(path=screenshot_path)
        finally:
            browser.close()
            
    caption = f"🎯 *【Pinnacle 英超盘口·精准锁定监控】*\n🕒 时间: `{current_time}`\n🚀 状态: 容器级精准对焦"
    if os.path.exists(screenshot_path):
        send_telegram_photo(screenshot_path, caption)

def main():
    capture_pinnacle_epl_exact()

if __name__ == "__main__":
    main()
