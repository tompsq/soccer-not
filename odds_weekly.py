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

def capture_pinnacle_odds_container():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    screenshot_path = "pinnacle_epl_odds_only.png"
    
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
            
            # 2. 强力点击英超
            print("🎯 正在强制触发英超链接点击...")
            success = page.evaluate("""() => {
                const links = Array.from(document.querySelectorAll('a'));
                let target = links.find(el => el.textContent.includes('Premier League'));
                
                if (!target) {
                    const allEls = Array.from(document.querySelectorAll('div, span, li'));
                    target = allEls.find(el => el.textContent.trim() === 'England - Premier League');
                }
                
                if (target) {
                    target.scrollIntoView();
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
                page.locator("text=England - Premier League").first.click(force=True)
                
            print("⏳ 等待英超盘口数据渲染...")
            time.sleep(8)
            
            # 3. 核心大招：精准锁定英超盘口主容器进行局部截图，彻底告别两边的大片空白和极小的字
            print("📸 正在对英超核心盘口区域进行精准截图...")
            
            # 通过定位 "England - Premier League Odds" 所在的区块，往上寻找合适的父级容器作为截图对象
            target_element = page.locator("text=England - Premier League Odds").first
            
            if target_element.count() > 0:
                # 获取包含整个赛程赔率表格的父容器
                odds_box = target_element.locator("xpath=./ancestor::div[contains(@class, 'style_container') or contains(@class, 'content') or position()=5]").first
                if odds_box.count() > 0:
                    odds_box.screenshot(path=screenshot_path)
                else:
                    # 如果没找到特定父级，退回到页面主体特定区域截图
                    page.locator("text=England - Premier League Odds").locator("xpath=../../..").screenshot(path=screenshot_path)
            else:
                # 兜底：如果找不到就截取全页
                page.screenshot(path=screenshot_path, full_page=True)
                
            print("✅ 核心盘口精准截图完成")
            
        except Exception as e:
            print(f"异常: {e}")
            page.screenshot(path=screenshot_path)
        finally:
            browser.close()
            
    caption = f"🎯 *【Pinnacle 英超盘口·核心数据精简截图】*\n🕒 时间: `{current_time}`\n🚀 状态: 已裁剪两边空白，专注赔率"
    if os.path.exists(screenshot_path):
        send_telegram_photo(screenshot_path, caption)

def main():
    capture_pinnacle_odds_container()

if __name__ == "__main__":
    main()
