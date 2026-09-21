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

def capture_pinnacle_epl_by_search():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    screenshot_path = "pinnacle_epl_search.png"
    
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
            # 1. 访问总大厅
            target_url = "https://www.pinnacle.com/en/soccer/matchups"
            print(f"🌐 正在连接大盘主页: {target_url}")
            page.goto(target_url, timeout=45000, wait_until="domcontentloaded")
            time.sleep(6)
            
            # 2. 查找并点击页面的搜索按钮或输入框（Pinnacle 通常有全局搜索或筛选）
            print("🔍 正在尝试通过页面搜索定位英超...")
            
            # 尝试点击搜索图标或直接在页面中寻找搜索输入框
            search_input = page.locator("input[placeholder*='Search'], input[type='text']").first
            if search_input.is_visible():
                search_input.fill("Premier League")
                time.sleep(2)
                page.keyboard.press("Enter")
                time.sleep(5)
                print("✅ 搜索指令已发送")
            else:
                # 备用方案：如果找不到搜索框，直接用 JS 遍历并点击包含 Premier League 的侧边栏或链接
                clicked = page.evaluate("""() => {
                    const links = Array.from(document.querySelectorAll('a, div, span'));
                    const eplLink = links.find(el => {
                        const text = el.textContent.trim();
                        return text === 'Premier League' || text === 'English Premier League';
                    });
                    if (eplLink) {
                        eplLink.click();
                        return true;
                    }
                    return false;
                }""")
                if clicked:
                    print("✅ 通过菜单栏成功点击英超链接")
                    time.sleep(6)
                else:
                    print("⚠️ 未能触发搜索或点击，执行页面强行向下滚动方案")
                    page.evaluate("window.scrollBy(0, 1200)")
                    time.sleep(3)
            
            # 3. 截取当前高质量视口
            page.screenshot(path=screenshot_path, full_page=False)
            print("📸 英超页面高清截图成功")
            
        except Exception as e:
            print(f"异常: {e}")
            page.screenshot(path=screenshot_path)
        finally:
            browser.close()
            
    caption = f"🎯 *【Pinnacle 英超盘口·搜索直达监控】*\n🕒 时间: `{current_time}`\n🚀 状态: 模拟搜索与高清渲染"
    if os.path.exists(screenshot_path):
        send_telegram_photo(screenshot_path, caption)

def main():
    capture_pinnacle_epl_by_search()

if __name__ == "__main__":
    main()
