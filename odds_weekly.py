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

def capture_pinnacle_force_click():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    screenshot_path = "pinnacle_epl_force.png"
    
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
            target_url = "https://www.pinnacle.com/en/soccer/matchups"
            print(f"🌐 正在进入Pinnacle主页: {target_url}")
            page.goto(target_url, timeout=45000, wait_until="domcontentloaded")
            time.sleep(6)
            
            # 1. 点击 "LEAGUES" 标签
            print("📋 正在点击 LEAGUES...")
            page.evaluate("""() => {
                const tabs = Array.from(document.querySelectorAll('button, div, span, a'));
                const tab = tabs.find(el => el.textContent.trim().toUpperCase() === 'LEAGUES');
                if (tab) tab.click();
            }""")
            time.sleep(4)
            
            # 2. 深度强制点击：寻找包含 Premier League 的超链接或最上层可点击元素，并强制派发鼠标事件
            print("🎯 正在强制触发英超链接点击...")
            success = page.evaluate("""() => {
                // 优先找带有 href 或者 a 标签的
                const links = Array.from(document.querySelectorAll('a'));
                let target = links.find(el => el.textContent.includes('Premier League'));
                
                if (!target) {
                    // 如果没有 a 标签，找所有包含该文本的元素
                    const allEls = Array.from(document.querySelectorAll('div, span, li'));
                    target = allEls.find(el => el.textContent.trim() === 'England - Premier League');
                }
                
                if (target) {
                    // 滚动到可见区域
                    target.scrollIntoView();
                    // 强制派发点击事件
                    const clickEvent = new MouseEvent('click', {
                        view: window,
                        bubbles: true,
                        cancelable: true,
                        buttons: 1
                    });
                    target.dispatchEvent(clickEvent);
                    return true;
                }
                return false;
            }""")
            
            if not success:
                # 备用定位
                page.locator("text=England - Premier League").first.click(force=True)
                
            # 3. 额外等待页面路由跳转和数据加载
            print("⏳ 等待英超盘口数据渲染...")
            time.sleep(8)
            
            # 4. 截图保存
            page.screenshot(path=screenshot_path, full_page=True)
            print("📸 截图完成")
            
        except Exception as e:
            print(f"异常: {e}")
            page.screenshot(path=screenshot_path)
        finally:
            browser.close()
            
    caption = f"🎯 *【Pinnacle 英超盘口·强力点击监控】*\n🕒 时间: `{current_time}`\n🚀 状态: 强制派发点击事件"
    if os.path.exists(screenshot_path):
        send_telegram_photo(screenshot_path, caption)

def main():
    capture_pinnacle_force_click()

if __name__ == "__main__":
    main()
