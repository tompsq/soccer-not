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

def capture_pinnacle_click_red_circle():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    screenshot_path = "pinnacle_epl_clicked.png"
    
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
            print(f"🌐 正在连接大盘主页: {target_url}")
            page.goto(target_url, timeout=45000, wait_until="domcontentloaded")
            time.sleep(8) # 确保高亮轮播卡片完全渲染加载
            
            # 通过脚本精准寻找红圈内的文字并点击
            clicked = page.evaluate("""() => {
                const elements = Array.from(document.querySelectorAll('div, span, a, h3, h4'));
                // 寻找红圈中的英超标识文字
                const target = elements.find(el => {
                    const text = el.textContent.trim().toUpperCase();
                    return text.includes('ENGLAND - PREMIER LEAGUE') || text.includes('SOCCER - ENGLAND - PREMIER');
                });
                
                if (target) {
                    // 如果找到文字，直接点击它或它的可点击父级
                    let clickable = target.closest('a') || target.closest('div[role="button"]') || target;
                    clickable.click();
                    return true;
                }
                return false;
            }""")
            
            if clicked:
                print("🎯 成功点击红圈处的英超赛事入口！")
                time.sleep(6) # 等待页面跳转并渲染英超专区
            else:
                print("⚠️ 未能直接触发点击，尝试使用 Playwright 文本定位点击...")
                try:
                    page.get_by_text("England - Premier League", exact=False).first.click()
                    time.sleep(6)
                    print("✅ Playwright 文本点击成功")
                except Exception as sub_e:
                    print(f"备用点击失败: {sub_e}")
            
            # 截取跳转后的英超专区页面
            page.screenshot(path=screenshot_path, full_page=False)
            print("📸 英超专区高清截图成功")
            
        except Exception as e:
            print(f"异常: {e}")
            page.screenshot(path=screenshot_path)
        finally:
            browser.close()
            
    caption = f"🎯 *【Pinnacle 英超盘口·红圈直达监控】*\n🕒 时间: `{current_time}`\n🚀 状态: 焦点卡片精准点击"
    if os.path.exists(screenshot_path):
        send_telegram_photo(screenshot_path, caption)

def main():
    capture_pinnacle_click_red_circle()

if __name__ == "__main__":
    main()
