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

def capture_pinnacle_by_path():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    screenshot_path = "pinnacle_epl_path.png"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2, # 双倍高清缩放
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="zh-CN" # 使用中文环境，方便直接匹配“足球”和“联赛”
        )
        
        page = context.new_page()
        
        try:
            # 步骤 1：访问首页（图一）
            target_url = "https://www.pinnacle.com/zh-cn/soccer/matchups"
            print(f"🌐 正在进入Pinnacle主页: {target_url}")
            page.goto(target_url, timeout=45000, wait_until="domcontentloaded")
            time.sleep(5)
            
            # 步骤 2：点击“足球” (对应图一、图二中的足球分类)
            print("⚽ 正在点击“足球”分类...")
            clicked_soccer = page.evaluate("""() => {
                const elements = Array.from(document.querySelectorAll('div, span, a'));
                const soccerEl = elements.find(el => {
                    const text = el.textContent.trim();
                    return text === '足球' || text.startsWith('足球 ');
                });
                if (soccerEl) {
                    soccerEl.click();
                    return true;
                }
                return false;
            }""")
            
            if not clicked_soccer:
                # 备用：直接通过文字定位
                page.get_by_text("足球", exact=True).first.click()
            
            time.sleep(4)
            
            # 步骤 3：点击“联赛”选项卡 (对应图二到图三的“联赛”标签)
            print("📋 正在切换到“联赛”标签页...")
            clicked_leagues_tab = page.evaluate("""() => {
                const tabs = Array.from(document.querySelectorAll('button, div, span, a'));
                const tab = tabs.find(el => el.textContent.trim() === '联赛');
                if (tab) {
                    tab.click();
                    return true;
                }
                return false;
            }""")
            
            if not clicked_leagues_tab:
                page.get_by_text("联赛", exact=True).first.click()
                
            time.sleep(4)
            
            # 步骤 4：在联赛列表中寻找并点击“英格兰 - 超级联赛” (对应图三)
            print("🎯 正在定位并点击“英格兰 - 超级联赛”...")
            clicked_epl = page.evaluate("""() => {
                const items = Array.from(document.querySelectorAll('div, span, a'));
                const epl = items.find(el => {
                    const text = el.textContent.trim();
                    return text.includes('英格兰 - 超级联赛') || text.includes('Super League') || text.includes('Premier League');
                });
                if (epl) {
                    epl.click();
                    return true;
                }
                return false;
            }""")
            
            if not clicked_epl:
                page.get_by_text("英格兰 - 超级联赛", exact=False).first.click()
                
            time.sleep(6) # 等待英超独立盘口页面完全加载渲染
            print("✅ 成功进入英格兰超级联赛专属盘口！")
            
            # 步骤 5：截图发送
            page.screenshot(path=screenshot_path, full_page=False)
            print("📸 英超专区高清截图成功")
            
        except Exception as e:
            print(f"异常: {e}")
            page.screenshot(path=screenshot_path)
        finally:
            browser.close()
            
    caption = f"🎯 *【Pinnacle 英超盘口·路径导航直达】*\n🕒 时间: `{current_time}`\n🚀 状态: 体育项目 -> 足球 -> 联赛 -> 英超"
    if os.path.exists(screenshot_path):
        send_telegram_photo(screenshot_path, caption)

def main():
    capture_pinnacle_by_path()

if __name__ == "__main__":
    main()
